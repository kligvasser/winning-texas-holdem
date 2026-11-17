<script lang="ts">
  import PlayingCard from './PlayingCard.svelte'

  let {
    label,
    cards,
    highlight = [],
  }: { label: string; cards: string[]; highlight?: string[] } = $props()
</script>

<div class="row">
  <span class="label">{label}</span>
  <div class="cards">
    {#each cards as code, i (code)}
      <PlayingCard {code} highlight={highlight.includes(code)} order={i} />
    {/each}
  </div>
</div>

<style>
  .row {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--felt-muted);
  }
  .cards {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
</style>
