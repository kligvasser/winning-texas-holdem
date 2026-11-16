<script lang="ts">
  import { api, type DrillMeta, type DrillStats } from '../api'
  import { percent, seconds, signed, totals } from '../format'

  let stats = $state<DrillStats[] | null>(null)
  let titles = $state<Record<string, string>>({})
  let error = $state<string | null>(null)

  $effect(() => {
    Promise.all([api.stats(), api.drills()]).then(
      ([s, drills]: [DrillStats[], DrillMeta[]]) => {
        titles = Object.fromEntries(drills.map((d) => [d.key, d.title]))
        stats = s
      },
      (e: Error) => (error = e.message),
    )
  })

</script>

<h1>Progress</h1>

{#if error}
  <p role="alert">Could not load stats: {error}</p>
{:else if stats === null}
  <p>Loading…</p>
{:else if stats.length === 0}
  <p>No answers yet. Run a Math Lab session and your numbers will show up here.</p>
{:else}
  {@const sum = totals(stats)}
  <p class="summary">
    {sum.attempts} answers, {percent(sum.correct / sum.attempts)} correct.
  </p>
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
          <th scope="row">{titles[row.drill] ?? row.drill}</th>
          <td>{row.attempts}</td>
          <td>{percent(row.accuracy)}</td>
          <td>{row.mean_abs_error ?? '–'}</td>
          <td class:over={(row.bias ?? 0) > 0} class:under={(row.bias ?? 0) < 0}>
            {signed(row.bias)}
          </td>
          <td>{seconds(row.mean_ms)}</td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="note">
    Bias is your average signed error: positive means you overestimate, negative means you
    underestimate.
  </p>
{/if}

<style>
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
  }
  th[scope='row'],
  th:first-child {
    text-align: left;
  }
  .over {
    color: var(--bad);
  }
  .under {
    color: var(--info);
  }
  .note,
  .summary {
    color: var(--muted);
  }
</style>
