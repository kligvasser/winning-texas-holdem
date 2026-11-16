<script lang="ts">
  import { api, type PaintResult, type Spot, type SpotLeak } from '../api'
  import ActionLegend from '../components/ActionLegend.svelte'
  import RangeGrid from '../components/RangeGrid.svelte'
  import { percent } from '../format'
  import { href } from '../router.svelte'

  let { params = [] }: { params?: string[] } = $props()

  let spots = $state<Spot[] | null>(null)
  let leaks = $state<SpotLeak[]>([])
  let error = $state<string | null>(null)
  let painted = $state<string[]>([])
  let result = $state<PaintResult | null>(null)

  $effect(() => {
    Promise.all([api.spots(), api.leaks()]).then(
      ([s, l]: [Spot[], SpotLeak[]]) => {
        spots = s
        leaks = l
      },
      (e: Error) => (error = e.message),
    )
  })

  const actions = (s: Spot) => s.choices.filter((c) => c !== 'Fold')
  const spot = $derived(spots?.find((s) => s.id === params[0]))
  const paintAction = $derived(
    spot && params[1] === 'paint' && actions(spot).includes(params[2]) ? params[2] : undefined,
  )

  async function check(s: Spot, action: string) {
    try {
      result = await api.paint(s.id, action, painted)
    } catch (e) {
      error = (e as Error).message
    }
  }

  function reset() {
    painted = []
    result = null
  }
</script>

{#if error}
  <p role="alert">Preflop error: {error}</p>
{:else if spots === null}
  <p>Loading…</p>
{:else if params[0] && !spot}
  <p>Unknown spot “{params[0]}”. <a href={href('preflop')}>All spots</a></p>
{:else if spot && paintAction}
  <nav class="crumbs"><a href={href('preflop', spot.id)}>← {spot.position} chart</a></nav>
  <h1>Paint the range</h1>
  <p class="lead">
    {spot.position}: {spot.situation} Paint every hand that should <strong>{paintAction}</strong>,
    then check. Drag to paint several cells.
  </p>
  <RangeGrid
    {painted}
    onpaint={(classes) => (painted = classes)}
    diff={result ?? undefined}
    label="Your range"
  />
  <p class="count">{painted.length} hands painted</p>
  {#if result}
    <section class="result" aria-live="polite">
      <h2>{result.combos_wrong === 0 ? 'Perfect' : `${result.combos_wrong} combos off`}</h2>
      <p>
        {percent(result.accuracy, 1)} of all combos classified correctly.
        {#if result.missed.length}<br /><span class="missed">Missed:</span>
          {result.missed.join(', ')}{/if}
        {#if result.extra.length}<br /><span class="extra">Should not be here:</span>
          {result.extra.join(', ')}{/if}
      </p>
      <button type="button" onclick={reset}>Try again</button>
    </section>
  {:else}
    <div class="actions">
      <button type="submit" onclick={() => check(spot, paintAction)}>Check</button>
      <button type="button" onclick={reset}>Clear</button>
    </div>
  {/if}
{:else if spot}
  <nav class="crumbs"><a href={href('preflop')}>← All spots</a></nav>
  <h1>{spot.position}</h1>
  <p class="lead">{spot.situation}</p>
  <RangeGrid grid={spot.grid} label="{spot.position} chart" />
  <ActionLegend actions={spot.choices} frequencies={spot.frequencies} />
  <p>{spot.note}</p>
  <p class="source">{spot.source}</p>
  <div class="actions">
    {#each actions(spot) as action (action)}
      <a class="button" href={href('preflop', spot.id, 'paint', action)}>Paint the {action} range</a>
    {/each}
    <a class="button secondary" href={href('math-lab', spot.kind === 'open' ? 'preflop-open' : 'preflop-defend')}
      >Drill these spots</a
    >
  </div>
{:else}
  <h1>Preflop</h1>
  <p class="lead">
    Baseline charts for 6-max cash at 100bb. Study a chart, paint it from memory, then drill the
    hands at its edges.
  </p>
  {#if leaks.length}
    <h2>Your weakest spots</h2>
    <table>
      <thead>
        <tr><th scope="col">Spot</th><th scope="col">Answers</th><th scope="col">Accuracy</th><th scope="col">Most missed</th></tr>
      </thead>
      <tbody>
        {#each leaks as leak (leak.spot)}
          <tr>
            <th scope="row"><a href={href('preflop', leak.spot)}>{leak.position}: {leak.situation}</a></th>
            <td>{leak.attempts}</td>
            <td>{percent(leak.accuracy)}</td>
            <td>{leak.missed_hands.map((m) => m.hand).join(', ') || '–'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
  {#each [{ title: 'Opening (folded to you)', kind: 'open' }, { title: 'Facing a raise', kind: 'defend' }] as group (group.kind)}
    <h2>{group.title}</h2>
    <div class="grid">
      {#each spots.filter((s) => s.kind === group.kind) as s (s.id)}
        <a class="tile" href={href('preflop', s.id)}>
          <strong>{s.position}</strong>
          <span>{s.situation}</span>
          <span class="freq">Plays {percent(1 - s.frequencies.Fold)} of hands</span>
        </a>
      {/each}
    </div>
  {/each}
{/if}

<style>
  .lead,
  .source,
  .count,
  .freq {
    color: var(--muted);
  }
  .source,
  .count {
    font-size: 0.85rem;
  }
  .crumbs {
    margin-bottom: 0.75rem;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }
  .button {
    padding: 0.55rem 1rem;
    border-radius: 0.55rem;
    background: var(--accent);
    color: var(--on-accent);
    text-decoration: none;
    font-weight: 600;
  }
  .button.secondary {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
    gap: 0.75rem;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.9rem 1rem;
    border-radius: 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
  }
  .tile:hover {
    border-color: var(--accent);
  }
  .tile span {
    font-size: 0.9rem;
  }
  .result {
    padding: 1rem 1.25rem;
    border-radius: 0.75rem;
    background: var(--surface);
    margin-top: 0.5rem;
  }
  .result h2 {
    margin-top: 0;
  }
  .missed {
    color: var(--info);
    font-weight: 600;
  }
  .extra {
    color: var(--bad);
    font-weight: 600;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    padding: 0.45rem 0.6rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }
</style>
