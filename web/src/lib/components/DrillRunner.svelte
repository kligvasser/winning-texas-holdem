<script lang="ts">
  import { api, type DrillMeta, type GradeResult, type Question } from '../api'
  import AnswerInput from './AnswerInput.svelte'
  import Feedback from './Feedback.svelte'
  import QuestionView from './QuestionView.svelte'

  let {
    drills,
    random = Math.random,
  }: { drills: DrillMeta[]; random?: () => number } = $props()

  let question = $state<Question | null>(null)
  let result = $state<GradeResult | null>(null)
  let error = $state<string | null>(null)
  let busy = $state(false)
  let answered = $state(0)
  let correct = $state(0)
  let startedAt = 0

  const current = $derived(drills.find((d) => d.key === question?.drill))

  async function next() {
    busy = true
    error = null
    result = null
    try {
      const drill = drills[Math.floor(random() * drills.length)]
      question = await api.question(drill.key)
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
    void drills
    answered = 0
    correct = 0
    void next()
  })
</script>

<div class="runner">
  <header>
    <span class="drill-title">{current?.title ?? ''}</span>
    <span class="score" aria-label="Session score">{correct} / {answered}</span>
  </header>

  {#if error}
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
  .error {
    padding: 1rem;
    border-radius: 0.75rem;
    background: var(--surface);
    border-left: 5px solid var(--bad);
  }
</style>
