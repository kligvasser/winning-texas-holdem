<script lang="ts">
  import { onDestroy } from 'svelte'
  import { api, type DrillMeta, type GradeResult, type Question } from '../api'
  import { loadBest, saveBest } from '../speed'
  import AnswerInput from './AnswerInput.svelte'
  import Confetti from './Confetti.svelte'
  import QuestionView from './QuestionView.svelte'

  let {
    drills,
    roundKey,
    seconds = 60,
    now = Date.now,
    random = Math.random,
    flashMs = 700,
  }: {
    drills: DrillMeta[]
    /** Which round this is (a drill key or "mixed"), for the personal best. */
    roundKey: string
    seconds?: number
    now?: () => number
    random?: () => number
    flashMs?: number
  } = $props()

  let phase = $state<'ready' | 'running' | 'done'>('ready')
  let question = $state<Question | null>(null)
  let missed = $state<GradeResult | null>(null)
  let score = $state(0)
  let attempts = $state(0)
  let left = $state(0)
  let best = $state(0)
  let newBest = $state(false)
  let error = $state<string | null>(null)
  let busy = false
  let endsAt = 0
  let shownAt = 0
  let timer: ReturnType<typeof setInterval> | undefined
  let queue: Promise<Question>[] = []

  $effect(() => {
    best = loadBest(roundKey)
  })

  function refill() {
    while (queue.length < 3) {
      const drill = drills[Math.floor(random() * drills.length)]
      const next = api.question(drill.key)
      next.catch(() => {})
      queue.push(next)
    }
  }

  async function advance() {
    missed = null
    try {
      const next = queue.shift()!
      refill()
      question = await next
      shownAt = now()
    } catch (e) {
      error = (e as Error).message
      finish()
    }
  }

  function tick() {
    left = Math.max(0, endsAt - now())
    if (left === 0) finish()
  }

  function start() {
    score = 0
    attempts = 0
    error = null
    newBest = false
    question = null
    queue = []
    refill()
    phase = 'running'
    endsAt = now() + seconds * 1000
    left = seconds * 1000
    timer = setInterval(tick, 100)
    void advance()
  }

  function finish() {
    clearInterval(timer)
    phase = 'done'
    newBest = saveBest(roundKey, score)
    best = loadBest(roundKey)
  }

  async function choose(q: Question, choice: number | string | string[]) {
    if (busy || phase !== 'running') return
    busy = true
    try {
      const graded = await api.answer(q.id, choice, Math.round(now() - shownAt))
      if (phase !== 'running') return
      attempts += 1
      if (graded.correct) {
        score += 1
        await advance()
      } else {
        missed = graded
        await new Promise((resolve) => setTimeout(resolve, flashMs))
        if (phase === 'running') await advance()
      }
    } catch (e) {
      error = (e as Error).message
      finish()
    } finally {
      busy = false
    }
  }

  onDestroy(() => clearInterval(timer))
</script>

<section class="speed" aria-label="Speed round">
  {#if phase === 'ready'}
    <div class="intro">
      <h2>⚡ {seconds}-second speed round</h2>
      <p>Answer as many as you can. Correct answers move on instantly; a miss shows the answer.</p>
      <p class="best">Personal best: <strong>{best}</strong></p>
      <button type="button" class="go" onclick={start}>Start ⏎</button>
    </div>
  {:else if phase === 'running'}
    <div class="hud">
      <span class="score" aria-label="Speed score">⚡ {score}</span>
      <span class="clock" aria-label="Seconds left">{Math.ceil(left / 1000)}s</span>
    </div>
    <div class="timebar" aria-hidden="true">
      <span style:width="{(left / (seconds * 1000)) * 100}%"></span>
    </div>
    {#if question}
      {#key question.id}<QuestionView {question} />{/key}
      <AnswerInput
        {question}
        disabled={missed !== null}
        onsubmit={(v) => choose(question!, v)}
        answered={missed ?? undefined}
        skippable={false}
      />
      {#if missed}<p class="miss" role="status">Answer: {missed.expected}</p>{/if}
    {:else}
      <p>Dealing…</p>
    {/if}
  {:else}
    {#if newBest && score > 0}<Confetti />{/if}
    <div class="intro">
      <h2>{newBest && score > 0 ? 'New personal best!' : "Time's up"}</h2>
      <p class="big"><strong>{score}</strong> correct of {attempts}</p>
      <p class="best">Personal best: <strong>{best}</strong></p>
      {#if error}<p role="alert">Stopped early: {error}</p>{/if}
      <button type="button" class="go" onclick={start}>Play again</button>
    </div>
  {/if}
</section>

<svelte:window
  onkeydown={(e) => {
    if (phase !== 'running' && e.key === 'Enter' && !(e.target instanceof HTMLButtonElement)) start()
  }}
/>

<style>
  .intro {
    text-align: center;
    padding: 2rem 1rem;
    border-radius: 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .go {
    background: #f2b544;
    color: #1d1505;
    border-color: #f2b544;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 0.7rem 1.6rem;
  }
  .best,
  .miss {
    color: var(--muted);
  }
  .big {
    font-size: 1.4rem;
  }
  .big strong {
    font-size: 2.6rem;
    color: var(--accent);
  }
  .hud {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-weight: 800;
    font-size: 1.4rem;
    font-variant-numeric: tabular-nums;
  }
  .timebar {
    height: 8px;
    border-radius: 4px;
    background: var(--border);
    margin: 0.5rem 0 1rem;
    overflow: hidden;
  }
  .timebar span {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, var(--bad), #f2b544, var(--good));
    transition: width 0.1s linear;
  }
  .miss {
    font-weight: 600;
  }
</style>
