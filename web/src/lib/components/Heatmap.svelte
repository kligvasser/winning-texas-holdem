<script lang="ts">
  import type { Activity } from '../api'
  import { activityLevel, mondayOffset } from '../format'

  let { history }: { history: Activity['history'] } = $props()

  const blanks = $derived(history.length ? mondayOffset(history[0].date) : 0)
  const activeDays = $derived(history.filter((d) => d.answers > 0).length)
</script>

<figure class="heatmap">
  <div class="cells" role="img" aria-label="Practised on {activeDays} of the last {history.length} days">
    {#each { length: blanks } as _, i (i)}<span class="blank"></span>{/each}
    {#each history as day (day.date)}
      <span
        class="cell level-{activityLevel(day.answers)}"
        title="{day.date}: {day.answers} answers{day.answers ? `, ${day.correct} correct` : ''}"
      ></span>
    {/each}
  </div>
  <figcaption>
    <span>Less</span>
    {#each [0, 1, 2, 3, 4] as level (level)}<span class="cell level-{level}"></span>{/each}
    <span>More</span>
  </figcaption>
</figure>

<style>
  .heatmap {
    margin: 0;
    overflow-x: auto;
  }
  .cells {
    display: grid;
    grid-template-rows: repeat(7, 0.85rem);
    grid-auto-flow: column;
    grid-auto-columns: 0.85rem;
    gap: 3px;
  }
  .cell,
  .blank {
    width: 0.85rem;
    height: 0.85rem;
    border-radius: 3px;
  }
  .level-0 {
    background: var(--border);
  }
  .level-1 {
    background: color-mix(in srgb, var(--accent) 30%, var(--border));
  }
  .level-2 {
    background: color-mix(in srgb, var(--accent) 55%, var(--border));
  }
  .level-3 {
    background: color-mix(in srgb, var(--accent) 80%, var(--border));
  }
  .level-4 {
    background: var(--accent);
  }
  figcaption {
    display: flex;
    align-items: center;
    gap: 3px;
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--muted);
  }
  figcaption span:first-child {
    margin-right: 0.25rem;
  }
  figcaption span:last-child {
    margin-left: 0.25rem;
  }
</style>
