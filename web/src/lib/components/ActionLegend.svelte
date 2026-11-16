<script lang="ts">
  import { actionColor } from '../grid'

  let {
    actions,
    frequencies = undefined,
  }: { actions: string[]; frequencies?: Record<string, number> } = $props()
</script>

<ul class="legend">
  {#each actions as action (action)}
    <li>
      <span class="swatch" style:background={actionColor(action)}></span>
      {action}{#if frequencies?.[action] !== undefined}
        <span class="freq">{Math.round(frequencies[action] * 100)}%</span>{/if}
    </li>
  {/each}
</ul>

<style>
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    list-style: none;
    padding: 0;
    margin: 0.5rem 0;
    font-size: 0.9rem;
  }
  li {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .swatch {
    width: 0.9rem;
    height: 0.9rem;
    border-radius: 3px;
    border: 1px solid var(--border);
  }
  .freq {
    color: var(--muted);
  }
</style>
