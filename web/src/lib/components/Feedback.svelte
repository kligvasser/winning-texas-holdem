<script lang="ts">
  import type { GradeResult } from '../api'
  import { signed, until } from '../format'
  import CardRow from './CardRow.svelte'

  let {
    result,
    unit = '',
    onnext,
  }: { result: GradeResult; unit?: string; onnext: () => void } = $props()

  let button = $state<HTMLButtonElement>()
  $effect(() => {
    button?.focus()
  })
</script>

<section class="feedback" class:correct={result.correct} aria-live="polite">
  <h3>{result.correct ? 'Correct' : 'Not quite'}</h3>
  <p class="numbers">
    You said <strong>{result.response}{unit === '%' ? '%' : ''}</strong>, the answer is
    <strong>{result.expected}{unit === '%' ? '%' : ''}</strong>
    {#if result.error !== null && result.error !== 0}
      <span class="error">({signed(result.error, unit === '%' ? ' pts' : '')})</span>
    {/if}
  </p>
  <ul>
    {#each result.explanation as line, i (i)}
      <li>{line}</li>
    {/each}
  </ul>
  {#if result.review}
    <p class="review">
      Review recorded ({result.review.rating}). This drill comes back {until(result.review.due)}.
    </p>
  {/if}
  {#if result.highlight.length}
    <div class="key-cards"><CardRow label="Key cards" cards={result.highlight} /></div>
  {/if}
  <button bind:this={button} type="button" onclick={onnext}>Next ⏎</button>
</section>

<style>
  .feedback {
    margin-top: 1rem;
    padding: 1rem 1.25rem;
    border-radius: 0.75rem;
    border-left: 5px solid var(--bad);
    background: var(--surface);
  }
  .correct {
    border-left-color: var(--good);
  }
  h3 {
    margin: 0 0 0.4rem;
    color: var(--bad);
  }
  .correct h3 {
    color: var(--good);
  }
  .error {
    color: var(--muted);
  }
  .review {
    font-size: 0.9rem;
    color: var(--muted);
  }
  .key-cards {
    --card-w: 2.6rem;
    --felt-muted: var(--muted);
    margin-bottom: 1rem;
  }
  ul {
    padding-left: 1.2rem;
    line-height: 1.5;
  }
</style>
