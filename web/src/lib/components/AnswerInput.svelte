<script lang="ts">
  import type { Question } from '../api'

  let {
    question,
    disabled = false,
    onsubmit,
  }: {
    question: Question
    disabled?: boolean
    onsubmit: (value: number | string) => void
  } = $props()

  let text = $state('')
  let input = $state<HTMLInputElement>()

  $effect(() => {
    // Reset and focus whenever a new question arrives.
    void question.id
    text = ''
    input?.focus()
  })

  function submitNumber(event: SubmitEvent) {
    event.preventDefault()
    const value = Number(text.trim())
    if (disabled || text.trim() === '' || Number.isNaN(value)) return
    onsubmit(value)
  }

  function onkeydown(event: KeyboardEvent) {
    if (disabled || question.kind !== 'choice') return
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
      inputmode="decimal"
      autocomplete="off"
      aria-label="Your answer"
      placeholder="Your answer"
      {disabled}
    />
    {#if question.unit}<span class="unit">{question.unit}</span>{/if}
    <button type="submit" disabled={disabled || text.trim() === ''}>Check ⏎</button>
  </form>
{:else}
  <div class="choices" role="group" aria-label="Choices">
    {#each question.choices as choice, i (choice)}
      <button type="button" {disabled} onclick={() => onsubmit(choice)}>
        <kbd>{i + 1}</kbd>{choice}
      </button>
    {/each}
  </div>
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
  }
  kbd {
    font-size: 0.75rem;
    opacity: 0.6;
  }
</style>
