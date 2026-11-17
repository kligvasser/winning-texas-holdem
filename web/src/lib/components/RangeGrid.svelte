<script lang="ts">
  import { ALL_CELLS, actionColor } from '../grid'

  let {
    grid = undefined,
    highlight = undefined,
    painted = [],
    onpaint = undefined,
    paintAction = 'Raise',
    diff = undefined,
    weights = undefined,
    label = 'Range grid',
  }: {
    /** Action per cell, row-major (display mode). */
    grid?: string[][]
    /** A hand class to outline, e.g. the hand you were dealt. */
    highlight?: string
    /** Painted hand classes (paint mode). */
    painted?: string[]
    /** Called with the new painted set; enables paint mode. */
    onpaint?: (classes: string[]) => void
    /** The action being painted, which sets the paint colour. */
    paintAction?: string
    /** After checking a painted range: cells you missed and cells you added wrongly. */
    diff?: { missed: string[]; extra: string[] }
    /** Likelihood per cell (0-1), drawn as a heat map. */
    weights?: number[][]
    label?: string
  } = $props()

  const paintSet = $derived(new Set(painted))
  const missed = $derived(new Set(diff?.missed))
  const extra = $derived(new Set(diff?.extra))
  let dragValue: boolean | null = null
  let last: { row: number; col: number } | null = null
  let focusIndex = $state(0)
  let cells = $state<HTMLButtonElement[]>([])

  function setMany(classes: string[], value: boolean) {
    const next = new Set(paintSet)
    for (const cls of classes) {
      if (value) next.add(cls)
      else next.delete(cls)
    }
    if (next.size !== paintSet.size || classes.some((c) => paintSet.has(c) !== value)) {
      onpaint?.([...next])
    }
  }

  /** Cells on the straight line between two cells, so fast drags do not skip any. */
  function between(a: { row: number; col: number }, b: { row: number; col: number }): string[] {
    const steps = Math.max(Math.abs(b.row - a.row), Math.abs(b.col - a.col))
    return Array.from({ length: steps + 1 }, (_, i) => {
      const t = steps === 0 ? 0 : i / steps
      const row = Math.round(a.row + (b.row - a.row) * t)
      const col = Math.round(a.col + (b.col - a.col) * t)
      return ALL_CELLS[row * 13 + col].cls
    })
  }

  function start(event: PointerEvent, index: number) {
    // Touch: a tap toggles (handled on click) and a swipe scrolls the page.
    if (!onpaint || event.pointerType === 'touch') return
    event.preventDefault()
    const cell = ALL_CELLS[index]
    dragValue = !paintSet.has(cell.cls)
    last = cell
    focusIndex = index
    setMany([cell.cls], dragValue)
  }

  function move(event: PointerEvent) {
    if (dragValue === null || last === null) return
    const target = document.elementFromPoint(event.clientX, event.clientY)
    const index = target instanceof HTMLElement ? Number(target.dataset.index) : NaN
    if (Number.isNaN(index)) return
    const cell = ALL_CELLS[index]
    setMany(between(last, cell), dragValue)
    last = cell
  }

  function click(event: MouseEvent, index: number) {
    // Keyboard (detail 0) and touch taps toggle here; mouse presses were handled on pointerdown.
    const touch = (event as PointerEvent).pointerType === 'touch'
    if (onpaint && (event.detail === 0 || touch)) {
      const cls = ALL_CELLS[index].cls
      setMany([cls], !paintSet.has(cls))
    }
  }

  function keydown(event: KeyboardEvent, index: number) {
    const moves: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 13, ArrowUp: -13 }
    const delta = moves[event.key]
    if (delta === undefined) return
    event.preventDefault()
    const row = Math.floor(index / 13)
    const next = index + delta
    const sameRow = Math.floor(next / 13) === row
    if (next < 0 || next >= 169 || (Math.abs(delta) === 1 && !sameRow)) return
    focusIndex = next
    cells[next]?.focus()
  }

  function background(row: number, col: number, cls: string): string {
    if (weights) {
      const share = Math.round(weights[row][col] * 100)
      return `color-mix(in srgb, var(--act-raise) ${share}%, var(--act-fold))`
    }
    if (grid) return actionColor(grid[row][col])
    return paintSet.has(cls) ? actionColor(paintAction) : 'var(--act-fold)'
  }
</script>

<svelte:window onpointerup={() => ((dragValue = null), (last = null))} />

<div
  class="grid"
  class:paint={onpaint}
  role="grid"
  aria-label={label}
  tabindex="-1"
  onpointermove={move}
>
  {#each ALL_CELLS as cell, index (cell.cls)}
    {@const on = weights
      ? weights[cell.row][cell.col] >= 0.5
      : grid
        ? grid[cell.row][cell.col] !== 'Fold'
        : paintSet.has(cell.cls)}
    <button
      bind:this={cells[index]}
      type="button"
      role="gridcell"
      data-cls={cell.cls}
      data-index={index}
      class:on
      class:hl={cell.cls === highlight}
      class:missed={missed.has(cell.cls)}
      class:extra={extra.has(cell.cls)}
      aria-selected={on}
      aria-label={weights
        ? `${cell.cls}: ${Math.round(weights[cell.row][cell.col] * 100)}%`
        : grid
          ? `${cell.cls}: ${grid[cell.row][cell.col]}`
          : cell.cls}
      tabindex={onpaint && index === focusIndex ? 0 : -1}
      style:background={background(cell.row, cell.col, cell.cls)}
      onpointerdown={(e) => start(e, index)}
      onclick={(e) => click(e, index)}
      onkeydown={(e) => keydown(e, index)}
      onfocus={() => (focusIndex = index)}
    >
      {cell.cls}
    </button>
  {/each}
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(13, 1fr);
    gap: 2px;
    width: 100%;
    max-width: 34rem;
    padding: 2px;
    border-radius: 0.8rem;
    border: 3px solid var(--ink);
    box-shadow: var(--drop);
    overflow: hidden;
    background: var(--grid-gap);
    user-select: none;
  }
  .paint {
    touch-action: manipulation;
  }
  button {
    aspect-ratio: 1;
    padding: 0;
    border: none;
    box-shadow: none;
    transform: none;
    filter: none;
    border-radius: 3px;
    font-size: clamp(0.56rem, 1.7vw, 0.74rem);
    font-weight: 700;
    color: var(--act-fold-text);
    cursor: default;
    min-width: 0;
  }
  .paint button {
    cursor: pointer;
  }
  button.on {
    color: var(--act-on-text);
  }
  .hl {
    outline: 3px solid var(--text);
    outline-offset: -1px;
    position: relative;
    z-index: 1;
  }
  .missed {
    box-shadow: inset 0 0 0 3px var(--info);
  }
  .extra {
    background-image: repeating-linear-gradient(
      45deg,
      rgb(0 0 0 / 0.35) 0 3px,
      transparent 3px 7px
    ) !important;
    text-decoration: line-through;
  }
</style>
