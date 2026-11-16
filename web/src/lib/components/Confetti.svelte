<script lang="ts">
  let { pieces = 70, random = Math.random }: { pieces?: number; random?: () => number } = $props()

  const COLORS = ['#e2685a', '#f2b544', '#4f9d69', '#5b8def', '#b36bd6', '#ffffff']
  const bits = $derived(Array.from({ length: pieces }, (_, i) => ({
    left: random() * 100,
    delay: random() * 0.6,
    duration: 1.8 + random() * 1.4,
    drift: (random() - 0.5) * 160,
    spin: 360 + random() * 720,
    color: COLORS[i % COLORS.length],
    size: 6 + random() * 6,
  })))
</script>

<div class="confetti" aria-hidden="true">
  {#each bits as b, i (i)}
    <span
      style:left="{b.left}%"
      style:background={b.color}
      style:width="{b.size}px"
      style:height="{b.size * 0.45}px"
      style:animation-delay="{b.delay}s"
      style:animation-duration="{b.duration}s"
      style:--drift="{b.drift}px"
      style:--spin="{b.spin}deg"
    ></span>
  {/each}
</div>

<style>
  .confetti {
    position: fixed;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 50;
  }
  span {
    position: absolute;
    top: -20px;
    border-radius: 2px;
    animation-name: fall;
    animation-timing-function: cubic-bezier(0.25, 0.6, 0.4, 1);
    animation-fill-mode: forwards;
  }
  @keyframes fall {
    to {
      transform: translate(var(--drift), 105vh) rotate(var(--spin));
      opacity: 0.2;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .confetti {
      display: none;
    }
  }
</style>
