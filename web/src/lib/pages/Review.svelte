<script lang="ts">
  import { api, type HandDetail, type HandSummary, type PlayStats } from '../api'
  import DecisionList from '../components/DecisionList.svelte'
  import PokerTable from '../components/PokerTable.svelte'
  import { percent } from '../format'
  import { describe } from '../play'
  import { href } from '../router.svelte'

  let { selected = undefined }: { selected?: string } = $props()

  let list = $state<HandSummary[] | null>(null)
  let stats = $state<PlayStats | null>(null)
  let detail = $state<HandDetail | null>(null)
  let error = $state<string | null>(null)
  let mistakesOnly = $state(false)
  let at = $state(0) // which step of the replay is on the table

  $effect(() => {
    if (selected) {
      api.hand(Number(selected)).then(
        (d) => (detail = d),
        (e: Error) => (error = e.message),
      )
    } else {
      api.hands().then(
        (r) => {
          list = r.hands
          stats = r.stats
        },
        (e: Error) => (error = e.message),
      )
    }
  })

  const frames = $derived(detail?.record.frames ?? [])
  // The last step is the stored hand itself, with every card face up.
  const done = $derived(at >= frames.length - 1)
  const moment = $derived(detail?.record.decisions.find((d) => d.index === at + 1))
  const rate = (value: number | null) => (value === null ? '–' : percent(value))
  const signed = (value: number) => `${value > 0 ? '+' : ''}${value}bb`

  function go(to: number) {
    at = Math.max(0, Math.min(frames.length - 1, to))
  }

  function onkeydown(event: KeyboardEvent) {
    if (!frames.length) return
    if (event.key === 'ArrowRight') go(at + 1)
    else if (event.key === 'ArrowLeft') go(at - 1)
  }

  const shown = $derived(
    (list ?? [])
      .filter((h) => !mistakesOnly || h.mistakes > 0)
      .toSorted((a, b) => b.worst_loss_bb - a.worst_loss_bb || b.id - a.id),
  )
</script>

<svelte:window {onkeydown} />

{#if error}
  <p role="alert">Could not load hands: {error}</p>
{:else if selected}
  <nav class="crumbs"><a href={href('review')}>← All hands</a></nav>
  {#if detail}
    {@const names = detail.record.seats.map((s) => s.character)}
    <h1>Hand #{detail.id}</h1>
    <PokerTable hand={done ? detail.record.hand : frames[at]} seats={detail.record.seats} tick={at} />
    {#if frames.length}
      <div class="replay" role="group" aria-label="Replay">
        <button type="button" disabled={at === 0} onclick={() => go(0)}>⏮ Start</button>
        <button type="button" disabled={at === 0} onclick={() => go(at - 1)}>◀ Back</button>
        <span class="step">Step {at + 1} of {frames.length} · {frames[at].street}</span>
        <button type="submit" disabled={done} onclick={() => go(at + 1)}>Next ▶</button>
        <button type="button" disabled={done} onclick={() => go(frames.length)}>Show result ⏭</button>
      </div>
      {#if moment && !done}
        <h2>Your decision here</h2>
        <DecisionList decisions={[moment]} />
      {/if}
    {/if}
    {#if done}
      <h2>Your decisions</h2>
      <DecisionList decisions={detail.record.decisions} />
    {:else}
      <p class="hint">Step through the hand with the buttons or the ← → keys. The result stays hidden until the end.</p>
    {/if}
    <h2>Action log</h2>
    <ol class="log">
      {#each done ? detail.record.hand.log : detail.record.hand.log.slice(0, at + 2) as a, i (i)}<li>{a.street}: {describe(a, names)}</li>{/each}
    </ol>
  {:else}
    <p>Loading…</p>
  {/if}
{:else}
  <h1>Review</h1>
  {#if stats && list}
    {#if stats.hands === 0}
      <p>No hands yet. <a href={href('play')}>Play a few hands</a> and they will show up here.</p>
    {:else}
      <section class="tiles">
        <div><strong>{stats.hands}</strong><span>hands</span></div>
        <div>
          <strong class:won={stats.net_bb > 0} class:lost={stats.net_bb < 0}
            >{signed(stats.net_bb)}</strong
          ><span>{stats.bb_per_100}bb per 100 hands</span>
        </div>
        <div><strong>{rate(stats.vpip)}</strong><span>VPIP (hands played)</span></div>
        <div><strong>{rate(stats.pfr)}</strong><span>PFR (hands raised)</span></div>
        <div><strong>{rate(stats.three_bet)}</strong><span>3-bet · chances: {stats.three_bet_chances}</span></div>
        <div><strong>{rate(stats.cbet)}</strong><span>C-bet · chances: {stats.cbet_chances}</span></div>
        <div><strong>{rate(stats.wtsd)}</strong><span>Went to showdown · flops seen: {stats.flops_seen}</span></div>
        <div><strong>{rate(stats.wsd)}</strong><span>Won at showdown · showdowns: {stats.showdowns}</span></div>
      </section>
      {#if stats.hands < 30}
        <p class="hint">Small sample: these numbers settle down after a few dozen hands.</p>
      {/if}

      {#if stats.leaks.length}
        <h2>What to work on</h2>
        <ul class="leaks">
          {#each stats.leaks as leak (leak.key)}
            <li>
              <strong>{leak.title}</strong>
              <span>{leak.detail}</span>
              <a class="button" href={href(leak.page, leak.arg)}>{leak.label} →</a>
            </li>
          {/each}
        </ul>
      {/if}

      <h2>By position</h2>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Seat</th>
              <th scope="col">Hands</th>
              <th scope="col">Result</th>
              <th scope="col">VPIP</th>
              <th scope="col">PFR</th>
              <th scope="col" title="Big blinds given up in reviewed decisions">Review loss</th>
              <th scope="col">Mistakes</th>
            </tr>
          </thead>
          <tbody>
            {#each stats.positions as p (p.position)}
              <tr>
                <th scope="row">{p.position}</th>
                <td>{p.hands}</td>
                <td class:won={p.net_bb > 0} class:lost={p.net_bb < 0}>{signed(p.net_bb)}</td>
                <td>{rate(p.vpip)}</td>
                <td>{rate(p.pfr)}</td>
                <td class:lost={p.loss_bb > 0}>{p.loss_bb ? `−${p.loss_bb}bb` : '–'}</td>
                <td>{p.mistakes}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <h2>Hands</h2>
      <label class="filter"><input type="checkbox" bind:checked={mistakesOnly} /> Only hands with mistakes</label>
      <ul class="hands">
        {#each shown as h (h.id)}
          <li>
            <a href={href('review', String(h.id))}>
              <span class="cards">{h.hole.join(' ')}</span>
              <span class="board">{h.board.join(' ') || 'no flop'}</span>
              <span class="vs">{h.style}</span>
              <span class:won={h.net_bb > 0} class:lost={h.net_bb < 0}
                >{h.net_bb > 0 ? '+' : ''}{h.net_bb}bb</span
              >
              {#if h.mistakes}<span class="mistakes">{h.mistakes} mistake{h.mistakes > 1 ? 's' : ''} · −{h.worst_loss_bb}bb</span>{/if}
            </a>
          </li>
        {:else}
          <li class="empty">No hands with mistakes. Nice.</li>
        {/each}
      </ul>
    {/if}
  {:else}
    <p>Loading…</p>
  {/if}
{/if}

<style>
  .crumbs {
    margin-bottom: 0.75rem;
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
    gap: 1rem;
  }
  .tiles div {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.9rem;
    border-radius: 1.1rem;
    background: color-mix(in srgb, var(--tint) 30%, var(--surface));
    border: var(--line);
    box-shadow: var(--drop);
    text-align: center;
  }
  .tiles div:nth-child(1) { --tint: var(--skyblue); }
  .tiles div:nth-child(2) { --tint: var(--sun); }
  .tiles div:nth-child(3) { --tint: var(--mint); }
  .tiles div:nth-child(4) { --tint: var(--grape); }
  .tiles strong {
    font-size: 1.5rem;
  }
  .tiles span {
    font-size: 0.85rem;
    color: var(--muted);
  }
  .filter {
    display: inline-flex;
    align-items: center;
    font-weight: 700;
    gap: 0.4rem;
    margin: 1rem 0 0.5rem;
  }
  .hands {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.6rem;
  }
  .hands a {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    padding: 0.6rem 0.9rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: var(--line);
    box-shadow: var(--drop-sm);
    color: inherit;
    font-weight: 400;
    text-decoration: none;
    font-variant-numeric: tabular-nums;
  }
  .cards {
    font-weight: 700;
  }
  .board,
  .vs,
  .empty {
    color: var(--muted);
  }
  .won {
    color: var(--good);
    font-weight: 700;
  }
  .lost {
    color: var(--bad);
    font-weight: 700;
  }
  .mistakes {
    color: var(--bad);
  }
  .log,
  .hint {
    color: var(--muted);
  }
  .replay {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  .step {
    padding: 0.15rem 0.9rem;
    border-radius: 999px;
    border: var(--line);
    background: var(--sun);
    color: var(--on-bright);
    font-weight: 800;
    font-variant-numeric: tabular-nums;
  }
  .leaks {
    list-style: none;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
    gap: 1rem;
  }
  .leaks li {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding: 0.9rem 1rem;
    border-radius: 1.1rem;
    border: var(--line);
    box-shadow: var(--drop);
    background: color-mix(in srgb, var(--tomato) 22%, var(--surface));
  }
  .leaks span {
    font-size: 0.92rem;
    flex: 1;
  }
  .button {
    align-self: flex-start;
    padding: 0.4rem 0.9rem;
    border-radius: 0.9rem;
    border: var(--line);
    box-shadow: var(--drop-sm);
    background: linear-gradient(#ffe94d, var(--sun-deep));
    color: var(--on-bright);
    font-weight: 800;
    text-decoration: none;
  }
  .scroll {
    overflow-x: auto;
    border-radius: 1.1rem;
    background: var(--surface);
    border: var(--line);
    box-shadow: var(--drop);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    padding: 0.5rem 0.6rem;
    text-align: right;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th:first-child {
    text-align: left;
  }
  thead th {
    background: var(--accent-soft);
    font-weight: 900;
  }
  tbody tr:last-child > * {
    border-bottom: none;
  }
</style>
