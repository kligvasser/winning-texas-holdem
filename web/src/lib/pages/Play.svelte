<script lang="ts">
  import { api, type Coach, type PlayState, type PlayStyle } from '../api'
  import ActionBar from '../components/ActionBar.svelte'
  import DecisionList from '../components/DecisionList.svelte'
  import PokerTable from '../components/PokerTable.svelte'
  import { describe, toBb } from '../play'
  import { href } from '../router.svelte'

  let styles = $state<PlayStyle[] | null>(null)
  let game = $state<PlayState | null>(null)
  let coach = $state<Coach | null>(null)
  let showCoach = $state(false)
  let error = $state<string | null>(null)
  let busy = $state(false)

  $effect(() => {
    api.styles().then(
      (list) => (styles = list),
      (e: Error) => (error = e.message),
    )
  })

  const names = $derived<[string, string]>(['You', game?.style.name ?? 'Bot'])
  const hand = $derived(game?.hand)
  const yourTurn = $derived(!!game?.legal && hand?.current === 0)

  async function run(work: () => Promise<PlayState>) {
    if (busy) return // a second click or key press while a move is in flight
    busy = true
    error = null
    coach = null
    try {
      game = await work()
      if (showCoach && game.legal) coach = await api.coach(game.id)
    } catch (e) {
      error = (e as Error).message
    } finally {
      busy = false
    }
  }

  async function toggleCoach() {
    showCoach = !showCoach
    if (showCoach && game?.legal) coach = await api.coach(game.id).catch(() => null)
  }

  function onkeydown(event: KeyboardEvent) {
    if (event.key.toLowerCase() === 'n' && game?.hand.finished && !busy) {
      void run(() => api.nextHand(game!.id))
    }
  }
</script>

<svelte:window {onkeydown} />

{#if error}<p role="alert" class="error">{error}</p>{/if}

{#if !game}
  <h1>Play</h1>
  <p class="lead">
    Heads-up, 100bb, against a bot with a clear style. Every decision you make is reviewed after
    the hand.
  </p>
  {#if styles === null && !error}
    <p>Loading…</p>
  {:else if styles}
    <div class="styles">
      {#each styles as s (s.key)}
        <button type="button" class="style" disabled={busy} onclick={() => run(() => api.play(s.key))}>
          <strong>{s.name}</strong>
          <span>{s.blurb}</span>
        </button>
      {/each}
    </div>
  {/if}
  <p><a href={href('review')}>Review your past hands →</a></p>
{:else if hand}
  <header class="session">
    <span><strong>{game.style.name}</strong> · hand {game.hands_played + (hand.finished ? 0 : 1)}</span>
    <span class:won={game.net_bb > 0} class:lost={game.net_bb < 0} aria-label="Session result"
      >{game.net_bb > 0 ? '+' : ''}{game.net_bb}bb</span
    >
    <button type="button" class="link" onclick={() => ((game = null), (coach = null))}>Change opponent</button>
  </header>

  <PokerTable {hand} {names} />

  {#if yourTurn && game.legal}
    <ActionBar
      legal={game.legal}
      pot={hand.pot}
      currentBet={hand.bets[0]}
      disabled={busy}
      onact={(kind, to) => run(() => api.act(game!.id, kind, to))}
    />
    <label class="coach-toggle"><input type="checkbox" checked={showCoach} onchange={toggleCoach} /> Coach</label>
    {#if showCoach && coach}
      <p class="coach" aria-label="Coach">
        {#if coach.need !== null}Price: call {coach.to_call_bb}bb into {coach.pot_bb}bb needs
          <strong>{Math.round(coach.need * 100)}%</strong>.{/if}
        Your equity against the bot's likely range (top {Math.round(coach.range_share * 100)}%):
        <strong>{Math.round(coach.equity * 100)}%</strong>.
      </p>
    {/if}
  {/if}

  {#if hand.finished}
    <section class="result" aria-label="Hand result">
      <div class="head">
        <h2>
          {#if hand.net && hand.net[0] > 0}You win {toBb(hand.net[0])}bb{:else if hand.net && hand.net[0] < 0}You lose
            {toBb(-hand.net[0])}bb{:else}Split pot{/if}
        </h2>
        <button type="button" class="next" disabled={busy} onclick={() => run(() => api.nextHand(game!.id))}
          >Next hand <kbd>N</kbd></button
        >
      </div>
      <h3>Your decisions</h3>
      <DecisionList decisions={game.decisions} />
      <p class="note">
        Graded against the bot's likely range from its style and preflop actions; later betting is
        ignored, so treat the numbers as estimates.
      </p>
    </section>
  {/if}

  <details class="log">
    <summary>Action log</summary>
    <ol>
      {#each hand.log as a, i (i)}<li><span class="street">{a.street}</span> {describe(a, names)}</li>{/each}
    </ol>
  </details>
{/if}

<style>
  .lead,
  .note {
    color: var(--muted);
  }
  .styles {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
    gap: 0.75rem;
    margin: 1rem 0;
  }
  .style {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.3rem;
    text-align: left;
    padding: 1rem;
  }
  .style span {
    color: var(--muted);
    font-size: 0.9rem;
  }
  .session {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1rem;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }
  .won {
    color: var(--good);
    font-weight: 700;
  }
  .lost {
    color: var(--bad);
    font-weight: 700;
  }
  .link {
    border: none;
    background: none;
    padding: 0;
    color: var(--muted);
    text-decoration: underline;
  }
  .coach-toggle {
    display: inline-flex;
    gap: 0.4rem;
    margin-top: 0.6rem;
    color: var(--muted);
  }
  .coach {
    padding: 0.6rem 0.9rem;
    border-radius: 0.6rem;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .result {
    margin-top: 1rem;
    padding: 1rem 1.2rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }
  .head h2 {
    margin: 0;
  }
  .next {
    background: var(--accent);
    color: var(--on-accent);
    border-color: var(--accent);
    font-weight: 700;
  }
  .log {
    margin-top: 1rem;
    color: var(--muted);
  }
  .log ol {
    padding-left: 1.2rem;
  }
  .street {
    text-transform: capitalize;
    font-size: 0.8rem;
    opacity: 0.7;
  }
  .error {
    color: var(--bad);
  }
</style>
