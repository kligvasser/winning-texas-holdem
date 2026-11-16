<script lang="ts">
  import type { Question } from '../api'
  import { parseAnswer } from '../answer'

  let {
    question,
    disabled = false,
    onsubmit,
    answered = undefined,
  }: {
    question: Question
    disabled?: boolean
    onsubmit: (value: number | string) => void
    /** After grading: what you chose and what was right, to mark the choice buttons. */
    answered?: { response: number | string; expected: number | string }
  } = $props()

  let text = $state('')
  let invalid = $state(false)
  let input = $state<HTMLInputElement>()
  let group = $state<HTMLDivElement>()

  $effect(() => {
    // Reset and focus whenever a new question arrives.
    void question.id
    text = ''
    invalid = false
    input?.focus()
    group?.querySelector('button')?.focus()
  })

  function submitNumber(event: SubmitEvent) {
    event.preventDefault()
    if (disabled) return
    const value = parseAnswer(text, question.unit)
    invalid = value === null
    if (value !== null) onsubmit(value)
  }

  function onkeydown(event: KeyboardEvent) {
    if (disabled || question.kind !== 'choice') return
    // Leave browser shortcuts (Cmd+1 switches tabs) and held keys alone.
    if (event.metaKey || event.ctrlKey || event.altKey || event.repeat) return
    if (event.target instanceof HTMLInputElement) return
    const index = Number(event.key) - 1
    if (Number.isInteger(index) && index >= 0 && index < question.choices.length) {
      onsubmit(question.choices[index])
    }
  }
</script>

<svelte:window {onkeydown} />

{#if question.kind === 'number'}
  <form class="number" onsubmit={submitNumber}>
    <input
      bind:this={input}
      bind:value={text}
      oninput={() => (invalid = false)}
      inputmode="decimal"
      autocomplete="off"
      aria-label="Your answer"
      aria-invalid={invalid}
      aria-describedby="answer-hint"
      placeholder={question.unit === '%' ? 'e.g. 25' : 'Your answer'}
      {disabled}
    />
    {#if question.unit}<span class="unit">{question.unit}</span>{/if}
    <button type="submit" disabled={disabled || text.trim() === ''}>Check ⏎</button>
  </form>
  <p id="answer-hint" class="hint" class:warn={invalid}>
    {#if invalid}
      Type a number, like 25, 25% or 1/3.
    {:else}
      Enter to check · S to skip
    {/if}
  </p>
{:else}
  <div class="choices" role="group" aria-label="Choices" bind:this={group}>
    {#each question.choices as choice, i (choice)}
      {@const right = answered?.expected === choice}
      {@const picked = answered?.response === choice}
      <button
        type="button"
        {disabled}
        class:right
        class:wrong={picked && !right}
        aria-describedby={picked ? 'picked-note' : undefined}
        onclick={() => onsubmit(choice)}
      >
        <kbd>{i + 1}</kbd>{choice}{#if right}<span class="mark" aria-label="correct answer">✓</span
          >{:else if picked}<span class="mark" aria-label="your answer">✗</span>{/if}
      </button>
    {/each}
  </div>
  {#if answered}<span id="picked-note" hidden>your answer</span>{/if}
  <p class="hint">Press 1–{question.choices.length} to answer · S to skip</p>
{/if}

<style>
  .number {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  input {
    font-size: 1.3rem;
    width: 9rem;
    padding: 0.5rem 0.75rem;
  }
  input[aria-invalid='true'] {
    border-color: var(--bad);
  }
  .unit {
    font-size: 1.1rem;
    color: var(--muted);
  }
  .choices {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
    gap: 0.5rem;
  }
  .choices button {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    text-align: left;
    padding: 0.7rem 1rem;
    transition:
      transform 0.08s ease,
      border-color 0.15s;
  }
  .choices button:active:not(:disabled) {
    transform: scale(0.97);
  }
  .choices button.right {
    border-color: var(--good);
    box-shadow: inset 0 0 0 1px var(--good);
    opacity: 1;
  }
  .choices button.wrong {
    border-color: var(--bad);
    box-shadow: inset 0 0 0 1px var(--bad);
    opacity: 1;
  }
  .mark {
    margin-left: auto;
    font-weight: 700;
  }
  .right .mark {
    color: var(--good);
  }
  .wrong .mark {
    color: var(--bad);
  }
  kbd {
    font-size: 0.75rem;
    color: var(--muted);
  }
  @media (pointer: coarse) {
    kbd,
    .hint:not(.warn) {
      display: none;
    }
  }
  .hint {
    margin: 0.4rem 0 0;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .warn {
    color: var(--bad);
  }
</style>
