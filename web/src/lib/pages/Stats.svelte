<script lang="ts">
  import { api, type Activity, type DrillMeta, type DrillStats } from '../api'
  import Heatmap from '../components/Heatmap.svelte'
  import { EXTRA_TITLES, fixed, percent, seconds, signed, totals } from '../format'
  import { href } from '../router.svelte'

  let stats = $state<DrillStats[] | null>(null)
  let activity = $state<Activity | null>(null)
  let titles = $state<Record<string, string>>({})
  let error = $state<string | null>(null)

  $effect(() => {
    Promise.all([api.stats(), api.drills(), api.activity()]).then(
      ([s, drills, a]: [DrillStats[], DrillMeta[], Activity]) => {
        titles = { ...EXTRA_TITLES, ...Object.fromEntries(drills.map((d) => [d.key, d.title])) }
        stats = [...s].sort((x, y) => x.accuracy - y.accuracy)
        activity = a
      },
      (e: Error) => (error = e.message),
    )
  })

  const drillLink = (key: string) => (key in EXTRA_TITLES ? href('preflop') : href('math-lab', key))
</script>

<h1>Progress</h1>
<p class="note"><a href={href('review')}>Review your played hands →</a></p>

{#if error}
  <p role="alert">Could not load stats: {error}</p>
{:else if stats === null || activity === null}
  <p>Loading…</p>
{:else if stats.length === 0}
  <p>No answers yet. Run a <a href={href('today')}>daily session</a> and your numbers will show up here.</p>
{:else}
  {@const sum = totals(stats)}
  <section class="tiles">
    <div><strong>🔥 {activity.streak}</strong><span>day streak</span></div>
    <div><strong>{activity.best_streak}</strong><span>best streak</span></div>
    <div><strong>{sum.attempts}</strong><span>answers</span></div>
    <div><strong>{percent(sum.correct / sum.attempts)}</strong><span>correct</span></div>
  </section>

  <h2>Last 12 weeks</h2>
  <Heatmap history={activity.history} />

  <h2>By drill <small>weakest first</small></h2>
  <div class="scroll">
    <table>
      <thead>
        <tr>
          <th scope="col">Drill</th>
          <th scope="col">Answers</th>
          <th scope="col">Accuracy</th>
          <th scope="col">Mean error</th>
          <th scope="col" title="Positive means you tend to overestimate">Bias</th>
          <th scope="col">Avg time</th>
        </tr>
      </thead>
      <tbody>
        {#each stats as row (row.drill)}
          <tr>
            <th scope="row"><a href={drillLink(row.drill)}>{titles[row.drill] ?? row.drill}</a></th>
            <td>{row.attempts}</td>
            <td>
              <span class="acc">
                <span class="bar" aria-hidden="true"
                  ><span
                    class:good={row.accuracy >= 0.8}
                    class:weak={row.accuracy < 0.6}
                    style:width={percent(row.accuracy)}
                  ></span></span
                >{percent(row.accuracy)}
              </span>
            </td>
            <td>{fixed(row.mean_abs_error)}</td>
            <td class:over={(row.bias ?? 0) > 0} class:under={(row.bias ?? 0) < 0}>
              {signed(row.bias)}
            </td>
            <td>{seconds(row.mean_ms)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="note">
    Bias is your average signed error: positive means you overestimate, negative means you
    underestimate. Click a drill to practise it.
  </p>
{/if}

<style>
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
    gap: 1rem;
  }
  .tiles div {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.9rem;
    border-radius: 1.1rem;
    background: color-mix(in srgb, var(--tint) 30%, var(--surface));
    border: var(--line);
    box-shadow: var(--drop);
  }
  .tiles div:nth-child(1) { --tint: var(--tomato); }
  .tiles div:nth-child(2) { --tint: var(--sun); }
  .tiles div:nth-child(3) { --tint: var(--skyblue); }
  .tiles div:nth-child(4) { --tint: var(--mint); }
  .tiles strong {
    font-size: 1.6rem;
    font-variant-numeric: tabular-nums;
  }
  .tiles span,
  small {
    color: var(--muted);
    font-size: 0.85rem;
    font-weight: 400;
  }
  .scroll {
    overflow-x: auto;
    border-radius: 1.1rem;
    background: var(--surface);
    border: var(--line);
    box-shadow: var(--drop);
    margin-bottom: 0.4rem;
  }
  thead th {
    background: var(--accent-soft);
    font-weight: 900;
  }
  tbody tr:last-child > * {
    border-bottom: none;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    padding: 0.5rem 0.6rem;
    text-align: right;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th[scope='row'],
  th:first-child {
    text-align: left;
  }
  th[scope='row'] a {
    color: inherit;
  }
  .acc {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
  }
  .bar {
    width: 4.5rem;
    height: 10px;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: var(--surface);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    background: var(--sun-deep);
  }
  .bar span.good {
    background: var(--good);
  }
  .bar span.weak {
    background: var(--bad);
  }
  .over {
    color: var(--bad);
  }
  .under {
    color: var(--info);
  }
  .note {
    color: var(--muted);
  }
</style>
