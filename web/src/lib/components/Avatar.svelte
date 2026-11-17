<script lang="ts">
  /** A cartoon face for a seat: the five bot styles, and a cat for you. */
  let {
    kind,
    mood = 'idle',
    label,
  }: { kind: string; mood?: 'idle' | 'happy' | 'out'; label: string } = $props()
</script>

{#snippet eyes(left: number, right: number, y: number, r: number)}
  {#each [left, right] as x (x)}
    {#if mood === 'happy'}
      <path class="line" d="M{x - r} {y + 2} Q{x} {y - r - 2} {x + r} {y + 2}" />
    {:else}
      <circle class="white" cx={x} cy={y} {r} />
      <circle class="ink" cx={x} cy={y + 1} r={r * 0.45} />
    {/if}
  {/each}
{/snippet}

<svg class="avatar {mood}" viewBox="0 0 100 100" role="img" aria-label={label} data-kind={kind}>
  {#if kind === 'nit'}
    <path fill="#6fbf4a" d="M40 20 Q44 6 52 16 Q58 4 62 20Z" />
    <path fill="#a3adc2" d="M18 70 Q8 40 30 26 Q48 10 70 22 Q94 34 86 64 Q84 88 52 90 Q22 92 18 70Z" />
    <path class="line thin" d="M66 26 L60 36 L68 40" />
    <path class="line" d="M26 42 L46 50 M74 42 L54 50" />
    {@render eyes(38, 62, 58, 6)}
    <path class="line" d={mood === 'happy' ? 'M38 72 Q50 82 62 72' : 'M40 75 H60'} />
  {:else if kind === 'tag'}
    <path fill="#2f6fe0" d="M50 2 L68 32 L36 30Z" />
    <ellipse fill="#3d8bff" cx="50" cy="58" rx="40" ry="33" />
    <ellipse class="white soft" cx="50" cy="76" rx="27" ry="14" />
    <path class="line" d="M26 40 L44 44 M74 40 L56 44" />
    {@render eyes(36, 64, 52, 7)}
    <path fill="#b3261e" d="M30 68 Q50 88 70 68Z" />
    <path class="white" d="M36 68 L41 76 L46 68 L50 77 L54 68 L59 76 L64 68Z" />
  {:else if kind === 'lag'}
    <path fill="#ff7a2f" d="M12 42 L18 4 L44 24Z M88 42 L82 4 L56 24Z" />
    <path fill="#2a1a3a" stroke="none" d="M18 4 L21 18 L30 13Z M82 4 L79 18 L70 13Z" />
    <path fill="#ff7a2f" d="M10 44 Q50 18 90 44 Q82 76 50 94 Q18 76 10 44Z" />
    <path class="white soft" d="M20 62 Q50 52 80 62 Q70 80 50 94 Q30 80 20 62Z" />
    <path class="line" d="M26 46 L44 48 M74 46 L56 48" />
    {@render eyes(36, 64, 55, 6)}
    <circle class="ink" cx="50" cy="86" r="5" />
  {:else if kind === 'station'}
    <path class="line spout" d="M50 26 Q46 8 34 10 M50 26 Q54 8 66 10" />
    <ellipse fill="#2ec4c6" cx="50" cy="60" rx="43" ry="31" />
    <path fill="#c6f5ef" stroke="none" d="M14 70 Q50 98 86 70 Q70 86 50 87 Q30 86 14 70Z" />
    {@render eyes(27, 73, 54, 5)}
    <path class="line" d="M32 66 Q50 84 68 66" />
  {:else if kind === 'maniac'}
    <path fill="#fff1c9" d="M24 36 Q2 30 8 6 Q22 18 36 26Z M76 36 Q98 30 92 6 Q78 18 64 26Z" />
    <ellipse fill="#e5484d" cx="50" cy="56" rx="35" ry="33" />
    <path class="line" d="M24 34 L44 44 M76 34 L56 44" />
    {@render eyes(36, 64, 52, 7)}
    <ellipse fill="#ffb3a7" cx="50" cy="76" rx="20" ry="12" />
    <circle class="ink" cx="43" cy="75" r="3" /><circle class="ink" cx="57" cy="75" r="3" />
    <path class="line gold" d="M42 84 Q50 97 58 84" />
  {:else}
    <path fill="#ffb02e" d="M16 36 L22 6 L46 24Z M84 36 L78 6 L54 24Z" />
    <ellipse fill="#ffb02e" cx="50" cy="58" rx="39" ry="34" />
    <path fill="#2fa84f" d="M14 44 Q50 22 86 44 Q50 36 14 44Z" />
    {@render eyes(36, 64, 56, 8)}
    <path fill="#ff8fa3" d="M46 68 H54 L50 73Z" />
    <path class="line" d="M40 76 Q45 82 50 76 Q55 82 60 76" />
    <path class="line thin" d="M8 64 L24 68 M8 76 L24 74 M92 64 L76 68 M92 76 L76 74" />
  {/if}
</svg>

<style>
  .avatar {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
    stroke: #2a1a3a;
    stroke-width: 4.5;
    stroke-linejoin: round;
    stroke-linecap: round;
    transition: filter 0.3s;
  }
  .out {
    filter: grayscale(1) brightness(0.9);
    opacity: 0.85;
  }
  .happy {
    animation: cheer 0.5s ease-in-out infinite alternate;
  }
  @keyframes cheer {
    to {
      transform: translateY(-8%) rotate(4deg);
    }
  }
  .line {
    fill: none;
    stroke-width: 5.5;
  }
  .thin {
    stroke-width: 3;
  }
  .gold {
    stroke: #ffc928;
  }
  .spout {
    stroke: #8fdcff;
  }
  .white {
    fill: #fff;
  }
  .soft {
    stroke: none;
  }
  .ink {
    fill: #2a1a3a;
    stroke: none;
  }
  @media (prefers-reduced-motion: reduce) {
    .happy {
      animation: none;
    }
  }
</style>
