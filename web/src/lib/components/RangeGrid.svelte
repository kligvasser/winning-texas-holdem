<script lang="ts">
  import { ALL_CELLS, actionColor } from '../grid'

  let {
    grid = undefined,
    highlight = undefined,
    painted = [],
    onpaint = undefined,
    diff = undefined,
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
    /** After checking a painted range: cells you missed and cells you added wrongly. */
    diff?: { missed: string[]; extra: string[] }
    label?: string
  } = $props()

  const paintSet = $derived(new Set(painted))
  const missed = $derived(new Set(diff?.missed))
  const extra = $derived(new Set(diff?.extra))
  let dragValue: boolean | null = null

  function apply(cls: string, value: boolean) {
    if (paintSet.has(cls) === value) return
    const next = new Set(paintSet)
    if (value) next.add(cls)
    else next.delete(cls)
    onpaint?.([...next])
  }

  function start(event: PointerEvent, cls: string) {
    if (!onpaint) return
    event.preventDefault()
    dragValue = !paintSet.has(cls)
    apply(cls, dragValue)
  }

  function move(event: PointerEvent) {
    if (dragValue === null) return
    const target = document.elementFromPoint(event.clientX, event.clientY)
    const cls = target instanceof HTMLElement ? target.dataset.cls : undefined
    if (cls) apply(cls, dragValue)
  }

  function keyToggle(event: MouseEvent, cls: string) {
    // Keyboard activation (Enter/Space) arrives as a click with detail 0; pointer clicks were
    // already handled on pointerdown.
    if (onpaint && event.detail === 0) apply(cls, !paintSet.has(cls))
  }

  function background(row: number, col: number, cls: string): string {
    if (grid) return actionColor(grid[row][col])
    return paintSet.has(cls) ? 'var(--act-raise)' : 'var(--act-fold)'
  }
</script>

<svelte:window onpointerup={() => (dragValue = null)} />

<div
  class="grid"
  class:paint={onpaint}
  role="grid"
  aria-label={label}
  tabindex="-1"
  onpointermove={move}
>
  {#each ALL_CELLS as cell (cell.cls)}
    {@const on = grid ? grid[cell.row][cell.col] !== 'Fold' : paintSet.has(cell.cls)}
    <button
      type="button"
      role="gridcell"
      data-cls={cell.cls}
      class:on
      class:hl={cell.cls === highlight}
      class:missed={missed.has(cell.cls)}
      class:extra={extra.has(cell.cls)}
      aria-selected={on}
      aria-label={grid ? `${cell.cls}: ${grid[cell.row][cell.col]}` : cell.cls}
      tabindex={onpaint ? 0 : -1}
      style:background={background(cell.row, cell.col, cell.cls)}
      onpointerdown={(e) => start(e, cell.cls)}
      onclick={(e) => keyToggle(e, cell.cls)}
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
    user-select: none;
  }
  .paint {
    touch-action: none;
  }
  button {
    aspect-ratio: 1;
    padding: 0;
    border: none;
    border-radius: 3px;
    font-size: clamp(0.45rem, 1.6vw, 0.72rem);
    font-weight: 600;
    color: var(--act-fold-text);
    cursor: default;
    min-width: 0;
  }
  .paint button {
    cursor: pointer;
  }
  button.on {
    color: #fff;
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
    box-shadow: inset 0 0 0 3px var(--bad);
    text-decoration: line-through;
  }
</style>
