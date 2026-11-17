<script lang="ts">
  import type { DrillMeta } from '../api'
  import { percent, seconds } from '../format'
  import type { ResultRow } from '../session'
  import Confetti from './Confetti.svelte'
  import Avatar from './Avatar.svelte'

  let {
    results,
    drills,
    bestStreak,
    skipped = 0,
    onrestart,
    nextHref,
    nextLabel,
  }: {
    results: ResultRow[]
    drills: DrillMeta[]
    bestStreak: number
    skipped?: number
    onrestart: () => void
    nextHref: string
    nextLabel: string
  } = $props()

  const correct = $derived(results.filter((r) => r.correct).length)
  const accuracy = $derived(results.length ? correct / results.length : 0)
  const avgMs = $derived(
    results.length ? results.reduce((sum, r) => sum + r.ms, 0) / results.length : null,
  )
  const byDrill = $derived.by(() => {
    const rows = new Map<string, { n: number; ok: number }>()
    for (const r of results) {
      const row = rows.get(r.drill) ?? { n: 0, ok: 0 }
      row.n += 1
      row.ok += Number(r.correct)
      rows.set(r.drill, row)
    }
    return [...rows.entries()].map(([key, row]) => ({
      title: drills.find((d) => d.key === key)?.title ?? key,
      ...row,
    }))
  })
  const verdict = $derived(
    results.length === 0
      ? 'No answers this time.'
      : accuracy >= 0.9
        ? 'Outstanding. That is a winning session.'
        : accuracy >= 0.7
          ? 'Solid work. The misses are what the next review is for.'
          : 'Tough spots. Read the explanations; they come back sooner when you miss.',
  )
  const celebrate = $derived(results.length >= 5 && accuracy >= 0.8)
</script>

{#if celebrate}<Confetti />{/if}

<section class="summary" aria-label="Session summary">
  <div class="face" aria-hidden="true"><Avatar kind="hero" mood="happy" label="" /></div>
  <h2>Session complete</h2>
  <p class="verdict">{verdict}</p>
  <div class="tiles">
    <div class="tile big">
      <strong>{correct}<small>/{results.length}</small></strong><span>correct</span>
    </div>
    <div class="tile"><strong>{percent(accuracy)}</strong><span>accuracy</span></div>
    <div class="tile"><strong>🔥 {bestStreak}</strong><span>best streak</span></div>
    <div class="tile"><strong>{seconds(avgMs)}</strong><span>per answer</span></div>
  </div>
  {#if byDrill.length > 1}
    <ul class="drills">
      {#each byDrill as row (row.title)}
        <li>
          <span>{row.title}</span>
          <span class="bar"><span style:width={percent(row.ok / row.n)}></span></span>
          <span class="num">{row.ok}/{row.n}</span>
        </li>
      {/each}
    </ul>
  {/if}
  {#if skipped}<p class="muted">Skipped {skipped}.</p>{/if}
  <div class="actions">
    <button type="button" class="primary" onclick={onrestart}>Play again</button>
    <a class="button" href={nextHref}>{nextLabel}</a>
  </div>
</section>

<style>
  .summary {
    padding: 1.25rem;
    border-radius: 1.4rem;
    background: var(--surface);
    border: 3px solid var(--ink);
    box-shadow: 0 6px 0 var(--ink);
    animation: rise 0.35s ease-out;
  }
  .face {
    float: right;
    width: 4.5rem;
    height: 4.5rem;
  }
  h2 {
    margin-top: 0;
  }
  .verdict,
  .muted {
    color: var(--muted);
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
    gap: 0.6rem;
    margin: 1rem 0;
  }
  .tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.75rem;
    border-radius: 1rem;
    border: var(--line);
    box-shadow: var(--drop-sm);
    background: color-mix(in srgb, var(--tint) 30%, var(--surface));
  }
  .tile:nth-child(1) { --tint: var(--mint); }
  .tile:nth-child(2) { --tint: var(--skyblue); }
  .tile:nth-child(3) { --tint: var(--tomato); }
  .tile:nth-child(4) { --tint: var(--grape); }
  .tile strong {
    font-size: 1.5rem;
    font-variant-numeric: tabular-nums;
  }
  .tile small {
    font-size: 1rem;
    color: var(--muted);
  }
  .tile span {
    font-size: 0.8rem;
    color: var(--muted);
  }
  .drills {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.4rem;
  }
  .drills li {
    display: grid;
    grid-template-columns: minmax(7rem, 1fr) 2fr 3rem;
    gap: 0.6rem;
    align-items: center;
    font-size: 0.9rem;
  }
  .bar {
height: 10px;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: var(--surface);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    background: var(--accent);
  }
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .primary {
    background: linear-gradient(#ffe94d, var(--sun-deep));
    color: var(--on-bright);
    font-weight: 900;
  }
  .button {
    padding: 0.55rem 1rem;
    border-radius: 0.9rem;
    border: var(--line);
    box-shadow: var(--drop-sm);
    background: var(--surface);
    font-weight: 800;
    color: var(--text);
    text-decoration: none;
  }
  @media (prefers-reduced-motion: reduce) {
    .summary {
      animation: none;
    }
  }
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
  }
</style>
