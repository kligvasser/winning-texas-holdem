<script lang="ts">
  let { value, goal, label }: { value: number; goal: number; label: string } = $props()
  const R = 42
  const C = 2 * Math.PI * R
  const share = $derived(Math.min(value / goal, 1))
</script>

<figure class="ring" aria-label="{label}: {value} of {goal}">
  <svg viewBox="0 0 100 100" aria-hidden="true">
    <circle class="track" cx="50" cy="50" r={R} />
    <circle
      class="fill"
      class:done={share >= 1}
      cx="50"
      cy="50"
      r={R}
      stroke-dasharray={C}
      stroke-dashoffset={C * (1 - share)}
    />
  </svg>
  <figcaption>
    <strong>{value}</strong><span>/ {goal}</span>
  </figcaption>
</figure>

<style>
  .ring {
    position: relative;
    width: 6.5rem;
    height: 6.5rem;
    margin: 0;
  }
  svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
  }
  circle {
    fill: none;
    stroke-width: 10;
  }
  .track {
    stroke: var(--border);
  }
  .fill {
    stroke: var(--accent);
    stroke-linecap: round;
    transition: stroke-dashoffset 0.8s ease;
  }
  .fill.done {
    stroke: #f2b544;
  }
  figcaption {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: baseline;
    justify-content: center;
    padding-top: 2.2rem;
    gap: 0.15rem;
  }
  strong {
    font-size: 1.4rem;
  }
  span {
    color: var(--muted);
    font-size: 0.85rem;
  }
</style>
