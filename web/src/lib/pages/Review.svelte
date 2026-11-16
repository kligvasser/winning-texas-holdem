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

  const shown = $derived(
    (list ?? [])
      .filter((h) => !mistakesOnly || h.mistakes > 0)
      .toSorted((a, b) => b.worst_loss_bb - a.worst_loss_bb || b.id - a.id),
  )
</script>

{#if error}
  <p role="alert">Could not load hands: {error}</p>
{:else if selected}
  <nav class="crumbs"><a href={href('review')}>← All hands</a></nav>
  {#if detail}
    {@const names: [string, string] = ['You', detail.style]}
    <h1>Hand #{detail.id} vs {detail.style}</h1>
    <PokerTable hand={detail.record.hand} {names} />
    <h2>Your decisions</h2>
    <DecisionList decisions={detail.record.decisions} />
    <h2>Action log</h2>
    <ol class="log">
      {#each detail.record.hand.log as a, i (i)}<li>{a.street}: {describe(a, names)}</li>{/each}
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
            >{stats.net_bb > 0 ? '+' : ''}{stats.net_bb}bb</strong
          ><span>{stats.bb_per_100}bb per 100 hands</span>
        </div>
        <div><strong>{percent(stats.vpip ?? 0)}</strong><span>VPIP (hands played)</span></div>
        <div><strong>{percent(stats.pfr ?? 0)}</strong><span>PFR (hands raised)</span></div>
      </section>
      <label class="filter"><input type="checkbox" bind:checked={mistakesOnly} /> Only hands with mistakes</label>
      <ul class="hands">
        {#each shown as h (h.id)}
          <li>
            <a href={href('review', String(h.id))}>
              <span class="cards">{h.hole.join(' ')}</span>
              <span class="board">{h.board.join(' ') || 'no flop'}</span>
              <span class="vs">vs {h.style}</span>
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
    gap: 0.75rem;
  }
  .tiles div {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.9rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: 1px solid var(--border);
    text-align: center;
  }
  .tiles strong {
    font-size: 1.5rem;
  }
  .tiles span {
    font-size: 0.85rem;
    color: var(--muted);
  }
  .filter {
    display: inline-flex;
    gap: 0.4rem;
    margin: 1rem 0 0.5rem;
  }
  .hands {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.4rem;
  }
  .hands a {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    padding: 0.6rem 0.9rem;
    border-radius: 0.6rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
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
  .log {
    color: var(--muted);
  }
</style>
