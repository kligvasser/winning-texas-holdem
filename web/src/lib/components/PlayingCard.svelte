<script lang="ts">
  import { parseCard } from '../cards'

  let {
    code,
    highlight = false,
    order = 0,
  }: { code: string; highlight?: boolean; order?: number } = $props()
  const face = $derived(parseCard(code))
</script>

<div
  class="card suit-{face.suit}"
  class:highlight
  role="img"
  aria-label={face.name}
  data-card={face.code}
  style:animation-delay="{order * 70}ms"
>
  <span class="corner">{face.rank}<span class="pip">{face.symbol}</span></span>
  <span class="center">{face.symbol}</span>
</div>

<style>
  .card {
    position: relative;
    width: var(--card-w, 3.4rem);
    height: calc(var(--card-w, 3.4rem) * 1.4);
    border-radius: 0.55rem;
    background: var(--card-bg);
    border: 2px solid #2a1a3a;
    box-shadow: 0 3px 0 rgb(42 26 58 / 0.6);
    color: var(--suit-color);
    font-weight: 900;
    flex: none;
    user-select: none;
    transition:
      transform 0.15s ease,
      box-shadow 0.15s ease;
    animation: deal 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.1) backwards;
  }
  @keyframes deal {
    from {
      opacity: 0;
      transform: translateY(-14px) rotate(-6deg) scale(0.92);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .card {
      animation: none;
    }
  }
  .highlight {
    transform: translateY(-4px);
    box-shadow:
      0 0 0 3px var(--sun),
      0 7px 0 rgb(42 26 58 / 0.6);
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
