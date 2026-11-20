<script lang="ts">
  import { untrack } from 'svelte'
  import type { Question } from '../api'
  import { parseAnswer } from '../answer'
  import { ALL_CELLS } from '../grid'
  import { ignoreHeld } from '../keys'
  import RangeGrid from './RangeGrid.svelte'

  const EVERY_HAND = ALL_CELLS.map((c) => c.cls)

  let {
    question,
    disabled = false,
    onsubmit,
    answered = undefined,
    skippable = true,
    startRange = undefined,
  }: {
    question: Question
    disabled?: boolean
    onsubmit: (value: number | string | string[]) => void
    /** After grading: what you chose and what was right, to mark the choice buttons. */
    answered?: { response: number | string; expected: number | string }
    /** Whether S skips (not in speed rounds). */
    skippable?: boolean
    /** Range questions: what to start from (your previous answer); every hand by default. */
    startRange?: string[]
  } = $props()

  let text = $state('')
  let painted = $state<string[]>([])
  let invalid = $state(false)
  let input = $state<HTMLInputElement>()
  let group = $state<HTMLDivElement>()
  let range = $state<HTMLDivElement>()

  $effect(() => {
    // Reset and focus whenever a new question arrives.
    void question.id
    text = ''
    invalid = false
    painted = untrack(() => startRange ?? EVERY_HAND)
    // Focus goes to the answer area, never onto a choice: a second Enter after "Next" would
    // otherwise answer the new question. Digits answer; Tab reaches the buttons.
    input?.focus()
    group?.focus()
    range?.querySelector<HTMLElement>('[role="grid"]')?.focus()
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

{#if question.kind === 'range'}
  <div class="range" bind:this={range}>
    <RangeGrid
      {painted}
      onpaint={disabled ? undefined : (classes) => (painted = classes)}
      label="Villain's range"
    />
    <div class="range-actions">
      <span class="count">{painted.length} of 169 hand classes</span>
      <button type="button" {disabled} onclick={() => (painted = [...EVERY_HAND])}>All</button>
      <button type="button" {disabled} onclick={() => (painted = [])}>Clear</button>
      <button type="submit" {disabled} onclick={() => onsubmit([...painted])}>Lock in</button>
    </div>
  </div>
{:else if question.kind === 'number'}
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
      Enter to check{skippable ? ' · S to skip' : ''}
    {/if}
  </p>
{:else}
  <div class="choices" role="group" aria-label="Choices" tabindex="-1" bind:this={group}>
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
        onkeydown={ignoreHeld}
      >
        <kbd>{i + 1}</kbd>{choice}{#if right}<span class="mark" aria-label="correct answer">✓</span
          >{:else if picked}<span class="mark" aria-label="your answer">✗</span>{/if}
      </button>
    {/each}
  </div>
  {#if answered}<span id="picked-note" hidden>your answer</span>{/if}
  <p class="hint">Press 1–{question.choices.length} to answer{skippable ? ' · S to skip' : ''}</p>
{/if}

<style>
  .range-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.6rem;
  }
  .count {
    color: var(--muted);
    margin-right: auto;
  }
  .number {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  input {
    font-size: 1.3rem;
    width: 9rem;
    padding: 0.5rem 0.75rem;
    font-weight: 800;
    border-width: 3px;
    box-shadow: inset 0 3px 0 rgb(0 0 0 / 0.08);
  }
  input[aria-invalid='true'] {
    border-color: var(--bad);
  }
  .unit {
    font-size: 1.1rem;
    color: var(--muted);
  }
  .choices:focus {
    outline: none;
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
  }
  .choices button.right {
    background: color-mix(in srgb, var(--mint) var(--wash-strong), var(--surface));
    opacity: 1;
  }
  .choices button.wrong {
    background: color-mix(in srgb, var(--tomato) var(--wash-strong), var(--surface));
    opacity: 1;
  }
  .mark {
    margin-left: auto;
    font-weight: 700;
    color: var(--text);
  }
  kbd {
    font-size: 0.75rem;
    min-width: 1.3rem;
    text-align: center;
    border-radius: 0.4rem;
    border: 1.5px solid currentColor;
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
