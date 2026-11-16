<script lang="ts">
  import type { GradeResult } from '../api'
  import { reviewMessage, signed } from '../format'
  import ActionLegend from './ActionLegend.svelte'
  import CardRow from './CardRow.svelte'
  import ClosenessMeter from './ClosenessMeter.svelte'
  import RangeGrid from './RangeGrid.svelte'

  let {
    result,
    unit = '',
    onnext,
  }: { result: GradeResult; unit?: string; onnext: () => void } = $props()

  let button = $state<HTMLButtonElement>()
  $effect(() => {
    button?.focus({ preventScroll: true })
  })

  const pct = $derived(unit === '%' ? '%' : '')
  const reading = $derived(!!result.reveal?.weights)
  const numeric = $derived(
    !reading && typeof result.expected === 'number' && typeof result.response === 'number',
  )
  const band = $derived(
    result.tolerance
      ? `answers within ±${result.tolerance}${unit === '%' ? ' pts' : ''} count`
      : 'the exact number is needed',
  )
</script>

<section class="feedback" class:correct={result.correct} aria-live="polite">
  <div class="head">
    <h3>{result.correct ? 'Correct' : 'Not quite'}</h3>
    <button bind:this={button} type="button" class="next" onclick={onnext}
      >{result.follow_up ? 'Next street ⏎' : 'Next ⏎'}</button
    >
  </div>
  {#if reading}
    <p class="numbers">
      Range match <strong>{result.response}%</strong> · best possible
      <strong>{result.expected}%</strong>
    </p>
  {:else}
  <p class="numbers">
    You said <strong>{result.response}{pct}</strong>, the answer is
    <strong>{result.expected}{pct}</strong>
    {#if result.error !== null && result.error !== 0}
      <span class="error">({signed(result.error, unit === '%' ? ' pts' : '')})</span>
    {/if}
    {#if numeric}<span class="band">· {band}</span>{/if}
  </p>
  {/if}
  {#if numeric && unit === '%'}
    <ClosenessMeter
      expected={result.expected as number}
      response={result.response as number}
      tolerance={result.tolerance ?? 0}
    />
  {/if}
  <ul>
    {#each result.explanation as line, i (i)}
      <li>{line}</li>
    {/each}
  </ul>
  {#if result.reveal?.weights}
    <details class="chart" open>
      <summary>{result.reveal.label ?? 'Real range'}</summary>
      <RangeGrid
        weights={result.reveal.weights}
        highlight={result.reveal.hand ?? undefined}
        label={result.reveal.label ?? 'Real range'}
      />
      <p class="band">Darker means more likely.{#if result.reveal.hand}
          The outlined cell is the hand it actually held.{/if}</p>
    </details>
  {/if}
  {#if result.reveal?.grid}
    <details class="chart" open>
      <summary>{result.reveal.label ?? 'Chart for this spot'}</summary>
      <RangeGrid
        grid={result.reveal.grid}
        highlight={result.reveal.hand ?? undefined}
        label={result.reveal.label ?? 'Chart for this spot'}
      />
      <ActionLegend actions={result.reveal.choices ?? []} />
    </details>
  {/if}
  {#if result.highlight.length}
    <div class="key-cards"><CardRow label="Key cards" cards={result.highlight} /></div>
  {/if}
  {#if result.review}
    <p class="review">{reviewMessage(result.review.rating, result.review.due)}</p>
  {/if}
</section>

<style>
  .feedback {
    animation: shake 0.38s ease;
    margin-top: 1rem;
    padding: 1rem 1.25rem;
    border-radius: 0.75rem;
    border-left: 5px solid var(--bad);
    background: var(--surface);
  }
  .correct {
    border-left-color: var(--good);
    animation: pop-in 0.3s cubic-bezier(0.3, 1.5, 0.5, 1);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }
  h3 {
    margin: 0;
    color: var(--bad);
    font-size: 1.25rem;
  }
  .correct h3 {
    color: var(--good);
  }
  .next {
    background: var(--accent);
    color: var(--on-accent);
    border-color: var(--accent);
    font-weight: 600;
  }
  .error,
  .band,
  .review {
    color: var(--muted);
  }
  .band,
  .review {
    font-size: 0.9rem;
  }
  ul {
    padding-left: 1.2rem;
    line-height: 1.5;
  }
  .chart {
    margin-bottom: 1rem;
  }
  .chart summary {
    cursor: pointer;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }
  .key-cards {
    --card-w: 2.6rem;
    --felt-muted: var(--muted);
    margin-bottom: 1rem;
  }
  @keyframes shake {
    20%,
    60% {
      transform: translateX(-5px);
    }
    40%,
    80% {
      transform: translateX(5px);
    }
  }
  @keyframes pop-in {
    from {
      transform: scale(0.97);
      opacity: 0.4;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .feedback {
      animation: none;
    }
  }
</style>
