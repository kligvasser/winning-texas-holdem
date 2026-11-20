<script lang="ts">
  import { api, type PlayStyle, type ToyFrequency, type ToyGame, type ToyOutcome, type ToyState } from '../api'
  import Avatar from '../components/Avatar.svelte'
  import LoadError from '../components/LoadError.svelte'
  import { percent } from '../format'
  import { href } from '../router.svelte'

  const LABELS: Record<string, string> = { bet: 'Bet 1', check: 'Check', call: 'Call 1', fold: 'Fold' }
  const PAST: Record<string, string> = { bet: 'bet', check: 'checked', call: 'called', fold: 'folded' }

  let menu = $state<{ games: ToyGame[]; opponents: PlayStyle[] } | null>(null)
  let picked = $state('akq')
  let game = $state<ToyState | null>(null)
  let reviewing = $state(false) // the last hand's result is on screen
  let error = $state<string | null>(null)
  let loadError = $state<string | null>(null)
  let busy = $state(false)
  let turn = 0 // bumped when an answer still in flight should be ignored
  let resultBox = $state<HTMLElement>()
  let actionBox = $state<HTMLElement>()

  function load() {
    loadError = null
    api.toyMenu().then(
      (m) => (menu = m),
      (e: Error) => (loadError = e.message),
    )
  }

  $effect(() => {
    load()
    return () => {
      turn += 1
    }
  })

  $effect(() => {
    // The action buttons and the result replace each other; keep keyboard focus beside them.
    void reviewing
    void game?.hands_played
    if (game && document.activeElement === document.body) {
      ;(resultBox ?? actionBox)?.focus({ preventScroll: true })
    }
  })

  function leave() {
    turn += 1
    busy = false
    game = null
  }

  const who = $derived(game?.opponent.character ?? '')
  const last = $derived(reviewing ? (game?.last ?? null) : null)

  const signed = (n: number) => `${n > 0 ? '+' : ''}${n}`
  const chips = (n: number) => `${Math.abs(n)} chip${Math.abs(n) === 1 ? '' : 's'}`
  const share = (f: ToyFrequency, key: 'yours' | 'optimal' | 'best') =>
    key === 'yours' ? (f.yours === null ? '–' : `${percent(f.yours)} of ${f.n}`) : percent(f[key])
  const story = (o: ToyOutcome, name: string) =>
    `${name} ${PAST[o.their_action]} with the ${o.their_card}. You ${o.chips > 0 ? 'won' : 'lost'} ${chips(o.chips)}.`

  async function run(call: () => Promise<ToyState>, review: boolean) {
    if (busy) return
    const mine = ++turn
    busy = true
    try {
      const next = await call()
      if (mine !== turn) return // you changed game while this was on its way
      game = next
      reviewing = review
      error = null
    } catch (e) {
      if (mine !== turn) return
      if ((e as { status?: number }).status === 404 && game) {
        // The server forgot this game (it restarted): back to the lobby.
        game = null
        error = 'That game is gone. Start a new one.'
      } else {
        error = (e as Error).message
      }
    } finally {
      if (mine === turn) busy = false
    }
  }

  const start = (opponent: string) => run(() => api.toyStart(picked, opponent), false)
  const act = (action: string) => run(() => api.toyAct(game!.id, action), true)

  function onkeydown(event: KeyboardEvent) {
    if (!game || busy || event.metaKey || event.ctrlKey || event.altKey) return
    const key = event.key.toLowerCase()
    if (reviewing) {
      // Enter on a focused button or link belongs to that control.
      const control = event.target instanceof HTMLButtonElement || event.target instanceof HTMLAnchorElement
      if (key === 'n' || (key === 'enter' && !control)) {
        event.preventDefault()
        reviewing = false
      }
      return
    }
    const action = game.hand.actions.find((a) => a[0] === key)
    if (action) void act(action)
  }
</script>

<svelte:window {onkeydown} />

{#if error}<p role="alert">Toy game error: {error}</p>{/if}

{#if !game}
  <nav class="crumbs"><a href={href('math-lab')}>← Math Lab</a></nav>
  <h1>Toy games</h1>
  <p class="lead">
    Tiny poker games you can solve completely. One card each, one bet: the bettor bets or checks,
    the caller calls or folds, the higher card wins. They make bluffing frequencies concrete.
  </p>
  {#if menu}
    <h2>1. Pick a game</h2>
    <div class="games">
      {#each menu.games as g (g.key)}
        <button type="button" class="game" aria-pressed={picked === g.key} onclick={() => (picked = g.key)}>
          <strong>{g.name}</strong>
          <span class="deck" aria-hidden="true">{#each g.cards as c (c)}<i>{c}</i>{/each}</span>
          <span>{g.blurb}</span>
        </button>
      {/each}
    </div>
    <h2>2. Pick an opponent</h2>
    <ul class="cast">
      {#each menu.opponents as o, i (o.key)}
        <li style:--i={i}>
          <span class="mug"><Avatar kind={o.key} label={o.character} /></span>
          <strong>{o.character}</strong>
          <em>{o.name}</em>
          <span>{o.blurb}</span>
          <button type="button" class="go" disabled={busy} onclick={() => start(o.key)}>Play {o.character}</button>
        </li>
      {/each}
    </ul>
  {:else if loadError}
    <LoadError message="Could not load the games: {loadError}" onretry={load} />
  {:else}
    <p>Loading…</p>
  {/if}
{:else}
  {@const hand = game.hand}
  {@const total = game.summary.chips}
  <div class="session">
    <span class="pill">{game.game.name}</span>
    <span class="pill">Hand {last ? game.hands_played - hand.before.length : hand.number}</span>
    <span class="pill" class:up={total > 0} class:down={total < 0} aria-label="Session result"
      >{signed(total)} chips</span
    >
    <button type="button" class="link" onclick={leave}>Change game</button>
  </div>

  <section class="felt" aria-label="Toy table">
    <div class="side">
      <span class="mug"><Avatar kind={game.opponent.key} mood={last && last.chips < 0 ? 'happy' : 'idle'} label={who} /></span>
      {#if last}
        <span class="card" aria-label="{who}'s card: {last.their_card}">{last.their_card}</span>
      {:else}
        <span class="card back" aria-label="{who}'s card is hidden"></span>
      {/if}
      <strong>{who}</strong>
    </div>
    <p class="say" aria-live="polite">
      {#if last}
        {last.role === 'bettor' && last.action === 'check'
          ? `You checked. ${who} shows the ${last.their_card}.`
          : last.role === 'bettor'
            ? `You bet. ${who} ${PAST[last.their_action]} with the ${last.their_card}.`
            : `${who} bet with the ${last.their_card}. You ${PAST[last.action]}.`}
      {:else if hand.role === 'bettor'}
        The pot is 2. You act: bet 1 chip or check.
      {:else}
        {who} bets 1 chip into 2. Call or fold?
      {/if}
    </p>
    <div class="side">
      <span class="mug"><Avatar kind="hero" mood={last && last.chips > 0 ? 'happy' : 'idle'} label="You" /></span>
      <span class="card" aria-label="Your card: {last ? last.card : hand.card}">{last ? last.card : hand.card}</span>
      <strong>You</strong>
    </div>
  </section>

  {#if last}
    <section class="result" class:won={last.chips > 0} aria-label="Hand result" tabindex="-1" bind:this={resultBox}>
      <h3>{last.chips > 0 ? `You win ${chips(last.chips)}!` : `You lose ${chips(last.chips)}`}</h3>
      <p class="lesson">{last.lesson}</p>
      <ul class="values">
        {#each Object.entries(last.values) as [action, value] (action)}
          <li class:best={action === last.best} class:yours={action === last.action}>
            <strong>{LABELS[action]}</strong>
            <span>{signed(value)} chips on average</span>
            {#if action === last.action}<em>your play</em>{/if}
          </li>
        {/each}
      </ul>
      <p class="note">
        Optimal play would {last.active} the {last.card} <strong>{percent(last.optimal)}</strong> of the time.
      </p>
      <button type="button" class="big" onclick={() => (reviewing = false)}>Next hand <kbd>N</kbd></button>
    </section>
  {:else}
    {#each hand.before as o, i (i)}
      <p class="before">Hand {hand.number - hand.before.length + i}: you held the {o.card}. {story(o, who)}</p>
    {/each}
    <div class="actions" role="group" aria-label="Your action" tabindex="-1" bind:this={actionBox}>
      {#each hand.actions as action (action)}
        <button type="button" class="act {action}" disabled={busy} onclick={() => act(action)}
          >{LABELS[action]} <kbd>{action[0].toUpperCase()}</kbd></button
        >
      {/each}
    </div>
  {/if}

  <section class="summary" aria-label="Session summary">
    <h3>How you are playing {who}</h3>
    <p class="note">
      Hands played: {game.hands_played}. Result: <strong>{signed(total)}</strong> chips. Your choices average
      <strong>{signed(game.summary.expected)}</strong>; the best choices would average
      <strong>{signed(game.summary.best)}</strong>.
    </p>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Card</th>
            <th scope="col">You bet</th>
            <th scope="col">Optimal</th>
            <th scope="col">Best vs {who}</th>
            <th scope="col">You call</th>
            <th scope="col">Optimal</th>
            <th scope="col">Best vs {who}</th>
          </tr>
        </thead>
        <tbody>
          {#each [...game.summary.cards].reverse() as row (row.card)}
            <tr>
              <th scope="row">{row.card}</th>
              <td>{share(row.bet, 'yours')}</td>
              <td>{share(row.bet, 'optimal')}</td>
              <td>{share(row.bet, 'best')}</td>
              <td>{share(row.call, 'yours')}</td>
              <td>{share(row.call, 'optimal')}</td>
              <td>{share(row.call, 'best')}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="note">{game.opponent.blurb}</p>
  </section>
{/if}

<style>
  .lead,
  .note {
    color: var(--muted);
  }
  .lead {
    max-width: 40rem;
    font-size: 1.05rem;
  }
  .crumbs {
    margin-bottom: 0.75rem;
  }
  .games {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
    gap: 1rem;
  }
  .game {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 1rem 1.1rem;
    border-radius: 1.1rem;
    border-width: 3px;
    box-shadow: var(--drop);
    text-align: left;
    font-weight: 400;
  }
  .game strong {
    font-size: 1.15rem;
    font-weight: 900;
  }
  .game[aria-pressed='true'] {
    background: var(--sun);
    color: var(--on-bright);
  }
  .deck {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  .deck i {
    font-style: normal;
    font-weight: 900;
    min-width: 1.6rem;
    padding: 0.15rem 0.3rem;
    text-align: center;
    border-radius: 0.4rem;
    border: 2px solid #2a1a3a;
    background: #fff;
    color: #2a1a3a;
  }
  .cast {
    list-style: none;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    gap: 1rem;
  }
  .cast li {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0.25rem;
    padding: 0.9rem 0.8rem;
    border-radius: 1.1rem;
    border: 3px solid var(--ink);
    background: color-mix(in srgb, var(--tint) var(--wash), var(--surface));
    box-shadow: 0 5px 0 var(--ink);
    animation: rise 0.4s cubic-bezier(0.3, 1.5, 0.5, 1) backwards;
    animation-delay: calc(var(--i) * 70ms);
  }
  .cast li:nth-child(1) { --tint: var(--skyblue); }
  .cast li:nth-child(2) { --tint: var(--mint); }
  .cast li:nth-child(3) { --tint: var(--grape); }
  .cast li:nth-child(4) { --tint: var(--tomato); }
  .cast em {
    font-style: normal;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0 0.5rem;
    border-radius: 999px;
    background: #2a1a3a;
    color: #fff;
  }
  .cast span:not(.mug) {
    font-size: 0.85rem;
    flex: 1;
  }
  .mug {
    display: block;
    width: 4.4rem;
    height: 4.4rem;
  }
  .go,
  .big {
    border-width: 3px;
    background: linear-gradient(#ffe94d, var(--sun-deep));
    color: var(--on-bright);
    font-weight: 900;
  }
  .big {
    padding: 0.7rem 1.6rem;
    font-size: 1.1rem;
  }
  .session {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.75rem;
  }
  .pill {
    padding: 0.15rem 0.9rem;
    border-radius: 999px;
    border: var(--line);
    background: var(--surface);
    font-weight: 800;
    box-shadow: var(--drop-sm);
  }
  .pill.up {
    background: var(--mint);
    color: var(--on-bright);
  }
  .pill.down {
    background: var(--tomato);
    color: var(--on-bright);
  }
  .link {
    margin-left: auto;
    border: none;
    box-shadow: none;
    background: none;
    padding: 0;
    color: var(--muted);
    text-decoration: underline;
  }
  .felt {
    display: grid;
    grid-template-columns: 1fr minmax(8rem, 1.4fr) 1fr;
    align-items: center;
    gap: 0.75rem;
    padding: 1.7rem;
    border-radius: 1.6rem;
    border: 3px solid var(--ink);
    box-shadow:
      inset 0 0 0 0.5rem var(--wood),
      inset 0 0 0 calc(0.5rem + 3px) var(--ink),
      0 6px 0 var(--ink);
    background: radial-gradient(ellipse at 50% 40%, var(--felt-a), var(--felt-b) 70%, var(--felt-c));
    color: #fff;
  }
  .result:focus,
  .actions:focus {
    outline: none;
  }
  .side {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
  }
  .card {
    display: grid;
    place-items: center;
    width: 4rem;
    height: 5.6rem;
    border-radius: 0.7rem;
    border: 3px solid #2a1a3a;
    background: #fff;
    color: #2a1a3a;
    font-size: 2.2rem;
    font-weight: 900;
    box-shadow: 0 4px 0 #2a1a3a;
    animation: rise 0.3s cubic-bezier(0.3, 1.5, 0.5, 1) backwards;
  }
  .card.back {
    background: repeating-linear-gradient(45deg, #e5484d 0 8px, #ff7a6b 8px 16px);
  }
  .say {
    margin: 0;
    padding: 0.5rem 0.9rem;
    border-radius: 1rem;
    border: 2px solid #2a1a3a;
    background: #fff;
    color: #2a1a3a;
    font-weight: 800;
    text-align: center;
    box-shadow: 0 3px 0 #2a1a3a;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1rem;
  }
  .act {
    padding: 0.8rem 1.8rem;
    border-width: 3px;
    font-size: 1.15rem;
    font-weight: 900;
    color: var(--on-bright);
    box-shadow: var(--drop);
  }
  .act.bet {
    background: var(--sun);
  }
  .act.call,
  .act.check {
    background: var(--mint);
  }
  .act.fold {
    background: var(--tomato);
  }
  kbd {
    font-size: 0.7rem;
    opacity: 0.7;
  }
  .before {
    margin: 0.75rem 0 0;
    color: var(--muted);
  }
  .result,
  .summary {
    margin-top: 1rem;
    padding: 1rem 1.25rem;
    border-radius: 1.2rem;
    border: 3px solid var(--ink);
    box-shadow: 0 5px 0 var(--ink);
    background: var(--surface);
  }
  .result {
    background: color-mix(in srgb, var(--tomato) var(--wash), var(--surface));
    animation: rise 0.3s cubic-bezier(0.3, 1.5, 0.5, 1);
  }
  .result.won {
    background: color-mix(in srgb, var(--mint) var(--wash), var(--surface));
  }
  h3 {
    margin: 0 0 0.5rem;
    font-size: 1.25rem;
    font-weight: 900;
  }
  .lesson {
    font-weight: 700;
  }
  .values {
    list-style: none;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  .values li {
    display: flex;
    flex-direction: column;
    padding: 0.5rem 0.9rem;
    border-radius: 0.9rem;
    border: var(--line);
    background: var(--surface);
  }
  .values li.best {
    background: var(--mint);
    color: var(--on-bright);
    box-shadow: var(--drop-sm);
  }
  .values em {
    font-style: normal;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
  }
  .scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    padding: 0.4rem 0.6rem;
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
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.96);
    }
  }
  @media (max-width: 560px) {
    .felt {
      grid-template-columns: 1fr 1fr;
      padding: 1.3rem 1rem;
    }
    .say {
      grid-column: 1 / -1;
      grid-row: 1;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .cast li,
    .card,
    .result {
      animation: none;
    }
  }
</style>
