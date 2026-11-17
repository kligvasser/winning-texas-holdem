<script lang="ts">
  import { untrack } from 'svelte'
  import { ApiError, api, type DrillMeta, type GradeResult, type Question } from '../api'
  import { percent } from '../format'
  import { href } from '../router.svelte'
  import type { ResultRow, SessionProgress } from '../session'
  import AnswerInput from './AnswerInput.svelte'
  import Feedback from './Feedback.svelte'
  import QuestionView from './QuestionView.svelte'
  import SessionSummary from './SessionSummary.svelte'

  let {
    drills,
    queue = undefined,
    random = Math.random,
    resume = undefined,
    onprogress = undefined,
  }: {
    /** Drills to pick from at random (free practice), and the source of titles. */
    drills: DrillMeta[]
    /** A fixed sequence of drill keys (the daily session). Ends when exhausted. */
    queue?: string[]
    random?: () => number
    /** Progress to continue from (a daily session interrupted by a reload). */
    resume?: SessionProgress
    /** Called after every answer or skip, so the caller can save progress. */
    onprogress?: (progress: SessionProgress) => void
  } = $props()

  let question = $state<Question | null>(null)
  let result = $state<GradeResult | null>(null)
  let error = $state<string | null>(null)
  let failed = $state<{ message: string; retry: (() => void) | null } | null>(null)
  let busy = $state(false)
  let finished = $state(false)
  let position = $state(0) // index into the queue, counting answered and skipped questions
  let results = $state<ResultRow[]>([])
  let skipped = $state(0)
  let streak = $state(0)
  let bestStreak = $state(0)
  let startedAt = 0
  let prefetched: { key: string; promise: Promise<Question> } | null = null
  let lastRange = $state<string[] | undefined>(undefined) // carried street to street (hand reading)

  const current = $derived(drills.find((d) => d.key === question?.drill))
  const correct = $derived(results.filter((r) => r.correct).length)

  function keyAt(index: number): string | undefined {
    return queue ? queue[index] : drills[Math.floor(random() * drills.length)].key
  }

  function prefetch() {
    const key = keyAt(position)
    if (key === undefined) return
    // Never throws here: a failure is surfaced by next(), when the question is actually needed.
    const promise = Promise.resolve().then(() => api.question(key))
    promise.catch(() => {})
    prefetched = { key, promise }
  }

  async function next() {
    // A scenario's next street was issued with the grade: show it straight away.
    const step = result?.follow_up
    if (!step) lastRange = undefined
    if (step) {
      result = null
      question = step
      startedAt = performance.now()
      return
    }
    const ready = prefetched
    prefetched = null
    const key = ready?.key ?? keyAt(position)
    if (key === undefined) {
      finished = true
      return
    }
    busy = true
    error = null
    try {
      const q = await (ready?.promise ?? api.question(key))
      result = null
      question = q
      startedAt = performance.now()
    } catch (e) {
      error = (e as Error).message
    } finally {
      busy = false
    }
  }

  async function submit(q: Question, value: number | string | string[]) {
    if (Array.isArray(value)) lastRange = value
    busy = true
    failed = null
    try {
      const ms = Math.round(performance.now() - startedAt)
      const graded = await api.answer(q.id, value, ms)
      result = graded
      // A multi-step scenario counts as one item of the session, finished at its last step.
      if (!graded.follow_up) position += 1
      results = [...results, { drill: q.drill, correct: graded.correct, ms }]
      streak = graded.correct ? streak + 1 : 0
      bestStreak = Math.max(bestStreak, streak)
      onprogress?.({ position, results, skipped })
      if (!graded.follow_up) prefetch()
    } catch (e) {
      // Keep the question on screen. A 404 means the server forgot it (it restarted).
      failed =
        e instanceof ApiError && e.status === 404
          ? { message: 'This question expired (the app restarted). Here is a fresh one.', retry: null }
          : { message: `Could not send your answer: ${(e as Error).message}`, retry: () => submit(q, value) }
      if (!failed.retry) void next()
    } finally {
      busy = false
    }
  }

  function skip() {
    if (busy || result) return
    position += 1
    skipped += 1
    onprogress?.({ position, results, skipped })
    void next()
  }

  function onkeydown(event: KeyboardEvent) {
    const typing = event.target instanceof HTMLInputElement && event.target.value !== ''
    if ((event.key === 's' || event.key === 'S') && !typing && question && !finished) {
      event.preventDefault()
      skip()
    }
  }

  function restart(from: SessionProgress = { position: 0, results: [], skipped: 0 }) {
    position = from.position
    results = from.results
    skipped = from.skipped
    streak = 0
    bestStreak = 0
    failed = null
    finished = false
    question = null
    result = null
    prefetched = null
    void next()
  }

  $effect(() => {
    // Restart only when the drills or queue change, not when the score does.
    void drills
    void queue
    untrack(() => restart(resume))
  })
</script>

<svelte:window {onkeydown} />

<div class="runner">
  <header>
    <span class="drill-title">{finished ? '' : current?.title}</span>
    <span class="right">
      {#if streak >= 2}
        {#key streak}<span class="combo" aria-label="Streak {streak}">🔥 {streak}</span>{/key}
      {/if}
      <span class="score" aria-label="Session score">{correct}/{results.length} correct</span>
    </span>
  </header>

  {#if queue}
    <div
      class="progress"
      role="progressbar"
      aria-label="Session progress"
      aria-valuemin={0}
      aria-valuemax={queue.length}
      aria-valuenow={position}
    >
      <div style:width={percent(position / queue.length)}></div>
    </div>
    {#if !finished}
      <p class="count">Question {Math.min(position + 1, queue.length)} of {queue.length}</p>
    {/if}
  {/if}

  {#if finished}
    <SessionSummary
      {results}
      {drills}
      {bestStreak}
      {skipped}
      onrestart={() => restart()}
      nextHref={queue ? href('learn') : href('math-lab')}
      nextLabel={queue ? 'Browse the curriculum' : 'Back to Math Lab'}
    />
  {:else if error}
    <div class="error" role="alert">
      <p>{error}</p>
      <button type="button" onclick={next}>Try again</button>
    </div>
  {:else if question}
    {#key question.id}<QuestionView {question} />{/key}
    <AnswerInput
      {question}
      disabled={busy || result !== null}
      onsubmit={(v) => submit(question!, v)}
      answered={result ?? undefined}
      startRange={lastRange}
    />
    {#if failed}
      <div class="failed" role="alert">
        <span>{failed.message}</span>
        {#if failed.retry}<button type="button" onclick={failed.retry}>Retry</button>{/if}
      </div>
    {/if}
    {#if result}
      <Feedback {result} unit={question.unit} onnext={next} />
    {:else}
      <div class="secondary">
        <button type="button" class="link" onclick={skip} disabled={busy}>Skip</button>
        {#if !queue && results.length}
          <button type="button" class="link" onclick={() => (finished = true)}>End session</button>
        {/if}
      </div>
    {/if}
  {:else}
    <p class="loading">Dealing…</p>
  {/if}
</div>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    min-height: 1.9rem;
  }
  .drill-title {
    font-weight: 800;
    color: var(--muted);
  }
  .right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .score {
    font-variant-numeric: tabular-nums;
    font-weight: 700;
  }
  .combo {
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    border: var(--line);
    box-shadow: var(--drop-sm);
    background: var(--sun);
    color: var(--on-bright);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    animation: pop 0.35s cubic-bezier(0.3, 1.6, 0.5, 1);
  }
  .progress {
    height: 14px;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: var(--surface);
    margin-bottom: 1rem;
    overflow: hidden;
  }
  .progress div {
    height: 100%;
    background: repeating-linear-gradient(-45deg, var(--sun) 0 8px, var(--sun-deep) 8px 16px);
    transition: width 0.3s ease;
  }
  .count {
    margin: -0.6rem 0 0.75rem;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .failed {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 0.75rem;
    padding: 0.6rem 0.9rem;
    border-radius: 0.9rem;
    border: var(--line);
    box-shadow: var(--drop-sm);
    background: color-mix(in srgb, var(--tomato) 30%, var(--surface));
  }
  .secondary {
    display: flex;
    gap: 1rem;
    margin-top: 0.75rem;
  }
  .link {
    border: none;
    box-shadow: none;
    background: none;
    padding: 0;
    color: var(--muted);
    text-decoration: underline;
  }
  .error {
    padding: 1rem 1.25rem;
    border-radius: 1.1rem;
    background: color-mix(in srgb, var(--tomato) 22%, var(--surface));
    border: var(--line);
    box-shadow: var(--drop);
  }
  @keyframes pop {
    from {
      transform: scale(0.6);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .combo {
      animation: none;
    }
  }
</style>
