<script lang="ts">
  import { parseCard } from '../cards'

  let { code, highlight = false }: { code: string; highlight?: boolean } = $props()
  const face = $derived(parseCard(code))
</script>

<div
  class="card suit-{face.suit}"
  class:highlight
  role="img"
  aria-label={face.name}
  data-card={face.code}
>
  <span class="corner">{face.rank}<span class="pip">{face.symbol}</span></span>
  <span class="center">{face.symbol}</span>
</div>

<style>
  .card {
    position: relative;
    width: var(--card-w, 3.4rem);
    height: calc(var(--card-w, 3.4rem) * 1.4);
    border-radius: 0.45rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    box-shadow: 0 2px 6px rgb(0 0 0 / 0.25);
    color: var(--suit-color);
    font-weight: 700;
    flex: none;
    user-select: none;
    transition:
      transform 0.15s ease,
      box-shadow 0.15s ease;
  }
  .highlight {
    transform: translateY(-4px);
    box-shadow:
      0 0 0 3px var(--accent),
      0 6px 14px rgb(0 0 0 / 0.3);
  }
  .corner {
    position: absolute;
    top: 0.2rem;
    left: 0.3rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    line-height: 1;
    font-size: 1rem;
  }
  .pip {
    font-size: 0.8rem;
  }
  .center {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    padding-top: 0.6rem;
    font-size: 1.7rem;
  }
  .suit-s {
    --suit-color: var(--suit-spades);
  }
  .suit-h {
    --suit-color: var(--suit-hearts);
  }
  .suit-d {
    --suit-color: var(--suit-diamonds);
  }
  .suit-c {
    --suit-color: var(--suit-clubs);
  }
</style>
