<script lang="ts">
  import { chipStack, toBb } from '../play'

  /** A pile of chips for an amount, in columns of five, with the amount written next to it. */
  let { chips, label, text = true }: { chips: number; label: string; text?: boolean } = $props()

  const columns = $derived.by(() => {
    const pile = chipStack(chips)
    const out: string[][] = []
    for (let i = 0; i < pile.length; i += 5) out.push(pile.slice(i, i + 5))
    return out
  })
</script>

<span class="stack" aria-label={label}>
  <span class="pile" aria-hidden="true">
    {#each columns as column, c (c)}
      <span class="column">
        {#each column as color, i (i)}<span class="chip {color}" style:--i={i}></span>{/each}
      </span>
    {/each}
  </span>
  {#if text}<span class="amount">{toBb(chips)}bb</span>{/if}
</span>

<style>
  .stack {
    display: inline-flex;
    align-items: flex-end;
    gap: 0.3rem;
  }
  .pile {
    display: inline-flex;
    align-items: flex-end;
    gap: 1px;
  }
  .column {
    display: inline-flex;
    flex-direction: column-reverse;
  }
  .chip {
    --c: #e5484d;
    --edge: #a3262b;
    width: var(--chip, 1.55rem);
    height: calc(var(--chip, 1.55rem) * 0.62);
    margin-top: calc(var(--chip, 1.55rem) * -0.42);
    border-radius: 50%;
    border: 2px solid #2a1a3a;
    background:
      radial-gradient(ellipse at center, var(--c) 0 46%, transparent 48%),
      repeating-conic-gradient(#fff 0 18deg, var(--c) 18deg 36deg);
    box-shadow: 0 3px 0 var(--edge), 0 3px 0 2px #2a1a3a;
    animation: drop 0.28s cubic-bezier(0.3, 1.5, 0.5, 1) backwards;
    animation-delay: calc(var(--i) * 45ms);
  }
  .column .chip:last-child {
    margin-top: 0;
  }
  .black {
    --c: #4a3a6b;
    --edge: #2a1a3a;
  }
  .green {
    --c: #2fa84f;
    --edge: #1c6e32;
  }
  .blue {
    --c: #3d8bff;
    --edge: #2259b8;
  }
  .white {
    --c: #ffd84a;
    --edge: #c79a12;
  }
  @keyframes drop {
    from {
      opacity: 0;
      transform: translateY(-14px);
    }
  }
  .amount {
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    background: #2a1a3a;
    color: #fff;
    font-weight: 800;
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  @media (prefers-reduced-motion: reduce) {
    .chip {
      animation: none;
    }
  }
</style>
