<script lang="ts">
  import { untrack } from 'svelte'
  import { api, type DrillMeta, type GradeResult, type Question } from '../api'
  import { percent } from '../format'
  import AnswerInput from './AnswerInput.svelte'
  import Feedback from './Feedback.svelte'
  import QuestionView from './QuestionView.svelte'

  let {
    drills,
    queue = undefined,
    random = Math.random,
  }: {
    /** Drills to pick from at random (free practice), and the source of titles. */
    drills: DrillMeta[]
    /** A fixed sequence of drill keys (the daily session). Ends when exhausted. */
    queue?: string[]
    random?: () => number
  } = $props()

  let question = $state<Question | null>(null)
  let result = $state<GradeResult | null>(null)
  let error = $state<string | null>(null)
  let busy = $state(false)
  let answered = $state(0)
  let correct = $state(0)
  let finished = $state(false)
  let startedAt = 0

  const current = $derived(drills.find((d) => d.key === question?.drill))

  function nextKey(): string | undefined {
    return queue ? queue[answered] : drills[Math.floor(random() * drills.length)].key
  }

  async function next() {
    const key = nextKey()
    if (key === undefined) {
      finished = true
      return
    }
    busy = true
    error = null
    result = null
    try {
      question = await api.question(key)
      startedAt = performance.now()
    } catch (e) {
      error = (e as Error).message
    } finally {
      busy = false
    }
  }

  async function submit(q: Question, value: number | string) {
    busy = true
    try {
      const elapsed = Math.round(performance.now() - startedAt)
      result = await api.answer(q.id, value, elapsed)
      answered += 1
      if (result.correct) correct += 1
    } catch (e) {
      error = (e as Error).message
    } finally {
      busy = false
    }
  }

  $effect(() => {
    // Restart only when the drills or queue change, not when the score does.
    void drills
    void queue
    untrack(() => {
      answered = 0
      correct = 0
      finished = false
      void next()
    })
  })
</script>

<div class="runner">
  <header>
    <span class="drill-title">{current?.title}</span>
    <span class="score" aria-label="Session score">{correct} / {answered}</span>
  </header>

  {#if queue}
    <div
      class="progress"
      role="progressbar"
      aria-label="Session progress"
      aria-valuemin={0}
      aria-valuemax={queue.length}
      aria-valuenow={answered}
    >
      <div style:width={percent(answered / queue.length)}></div>
    </div>
  {/if}

  {#if finished}
    <section class="done">
      <h2>Session complete</h2>
      <p>
        {correct} of {answered} correct. Reviews are scheduled; come back when more are due.
      </p>
    </section>
  {:else if error}
    <div class="error" role="alert">
      <p>{error}</p>
      <button type="button" onclick={next}>Try again</button>
    </div>
  {:else if question}
    <QuestionView {question} />
    <AnswerInput
      {question}
      disabled={busy || result !== null}
      onsubmit={(v) => submit(question!, v)}
    />
    {#if result}
      <Feedback {result} unit={question.unit} onnext={next} />
    {/if}
  {:else}
    <p class="loading">Dealing…</p>
  {/if}
</div>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.75rem;
  }
  .drill-title {
    font-weight: 600;
    color: var(--muted);
  }
  .score {
    font-variant-numeric: tabular-nums;
    font-weight: 700;
  }
  .progress {
    height: 6px;
    border-radius: 3px;
    background: var(--border);
    margin-bottom: 1rem;
    overflow: hidden;
  }
  .progress div {
    height: 100%;
    background: var(--accent);
    transition: width 0.3s ease;
  }
  .done,
  .error {
    padding: 1rem 1.25rem;
    border-radius: 0.75rem;
    background: var(--surface);
  }
  .done {
    border-left: 5px solid var(--good);
  }
  .error {
    border-left: 5px solid var(--bad);
  }
</style>
