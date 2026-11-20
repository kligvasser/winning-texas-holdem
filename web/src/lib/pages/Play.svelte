<script lang="ts">
  import { api, type Coach, type PlayState, type PlayStyle, type TableView } from '../api'
  import ActionBar from '../components/ActionBar.svelte'
  import Avatar from '../components/Avatar.svelte'
  import Confetti from '../components/Confetti.svelte'
  import DecisionList from '../components/DecisionList.svelte'
  import LoadError from '../components/LoadError.svelte'
  import PokerTable from '../components/PokerTable.svelte'
  import { describe, frameDelay, signedBb, toBb } from '../play'
  import { href } from '../router.svelte'
  import { play as chime, setSound, soundFor, soundOn, unlock } from '../sound'

  /** Milliseconds per bot action; 0 shows the newest position at once. */
  let { pace = 700 }: { pace?: number } = $props()

  const BIG_WIN = 10 // chips: 5bb

  let cast = $state<PlayStyle[] | null>(null)
  let castError = $state<string | null>(null)
  let said = $state('') // read out by screen readers: what just happened at the table
  let controls = $state<HTMLDivElement>()
  let game = $state<PlayState | null>(null)
  let coach = $state<Coach | null>(null)
  let showCoach = $state(false)
  let error = $state<string | null>(null)
  let busy = $state(false)
  let step = $state(0) // which frame of game.frames is on the table
  let tick = $state(0)
  let sweep = $state<number[] | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  let turn = 0 // bumped whenever an answer still in flight should be ignored
  let onTable: TableView | null = null // the last position shown, to see which bets just left
  let carry = $state(false)
  let sound = $state(soundOn())

  /** The cast is decoration: without it you can still be dealt in. */
  function loadCast() {
    castError = null
    api.styles().then(
      (list) => (cast = list),
      (e: Error) => (castError = e.message),
    )
  }

  $effect(() => {
    loadCast()
    return () => {
      turn += 1
      clearTimeout(timer)
    }
  })

  const names = $derived(game?.seats.map((s) => s.character) ?? [])
  const settled = $derived(!!game && step >= game.frames.length - 1)
  const table = $derived<TableView | null>(game ? (settled ? game.hand : game.frames[step]) : null)
  const yourTurn = $derived(settled && !!game?.legal)
  const over = $derived(settled && !!game?.hand.finished)
  const net = $derived(game?.hand.net?.[0] ?? 0)
  // While the bots' moves are still being shown, the log stops at the move on the table.
  const log = $derived(
    game ? game.hand.log.slice(0, game.hand.log.length - (settled ? 0 : game.frames.length - 1 - step)) : [],
  )
  const outcome = $derived(
    !game || !game.hand.finished
      ? ''
      : net > 0
        ? `You win ${toBb(net)}bb!`
        : net < 0
          ? `You lose ${toBb(-net)}bb`
          : `${game.hand.winners.map((w) => names[w]).join(' & ')} ${game.hand.winners.length > 1 ? 'split' : 'takes'} the pot`,
  )

  $effect(() => {
    // The buttons under the table come and go; keep keyboard focus next to them.
    void settled
    void over
    void yourTurn
    if (game && document.activeElement === document.body) controls?.focus({ preventScroll: true })
  })

  function show(index: number) {
    const frames = game!.frames
    const now = frames[index]
    const before = onTable ?? now
    onTable = now
    step = index
    tick += 1
    // Bets that left the seats since the last position are on their way to the pot.
    const cleared = now.bets.every((b) => b === 0) && before.bets.some((b) => b > 0)
    sweep = cleared ? before.bets : null
    const last = index === frames.length - 1
    said = last && outcome ? `${describe(now.last, names)}. ${outcome}` : describe(now.last, names)
    if (last && now.finished) chime(now.net![0] > 0 ? 'win' : now.net![0] < 0 ? 'lose' : 'chip')
    else chime(soundFor(now))
    if (index < frames.length - 1) {
      timer = setTimeout(() => show(index + 1), frameDelay(now, pace, now.folded[0]))
    }
  }

  function skip() {
    clearTimeout(timer)
    if (game && !settled) show(game.frames.length - 1)
  }

  async function run(work: () => Promise<PlayState>) {
    if (busy) return // a second click or key press while a move is in flight
    unlock() // still inside the click: browsers only let sound start from one
    const mine = ++turn
    busy = true
    error = null
    coach = null
    clearTimeout(timer)
    try {
      const next = await work()
      if (mine !== turn) return // you left the table while this was on its way
      game = next
      step = 0
      show(pace ? 0 : game.frames.length - 1)
      askCoach()
    } catch (e) {
      if (mine !== turn) return
      if ((e as { status?: number }).status === 404) {
        // The server forgot this table (it restarted): back to the lobby.
        leave()
        error = 'That table is gone. Deal a new one.'
      } else {
        error = (e as Error).message
      }
    } finally {
      if (mine === turn) busy = false
    }
  }

  /** The coach is a hint: it never blocks play, and a failed hint is just no hint. */
  function askCoach() {
    if (!showCoach || !game?.legal) return
    const mine = turn
    api.coach(game.id).then(
      (hint) => {
        if (mine === turn) coach = hint
      },
      () => {},
    )
  }

  function toggleCoach() {
    showCoach = !showCoach
    askCoach()
  }

  function toggleSound() {
    sound = !sound
    setSound(sound)
    if (sound) unlock()
  }

  function leave() {
    turn += 1
    busy = false
    clearTimeout(timer)
    game = null
    coach = null
    onTable = null
    said = ''
  }

  function onkeydown(event: KeyboardEvent) {
    if (!game || busy || event.metaKey || event.ctrlKey || event.altKey) return
    // Space and Enter on a focused button or box belong to that control.
    const control = event.target instanceof HTMLButtonElement || event.target instanceof HTMLInputElement
    if (event.key === ' ' && !settled && !control) {
      event.preventDefault()
      skip()
    } else if (event.key.toLowerCase() === 'n' && over) {
      void run(() => api.nextHand(game!.id))
    }
  }
</script>

<svelte:window {onkeydown} />

{#if error}<p role="alert" class="error">{error}</p>{/if}
<p class="sr-only" aria-live="polite" data-testid="said">{said}</p>

{#if !game}
  <section class="lobby">
    <h1>Play</h1>
    <p class="lead">
      Six seats, 100bb each, and five rivals who each play their own way. Spot their habits, take
      their chips, then see every decision you made reviewed.
    </p>
    {#if castError}
      <LoadError message="Could not load the rivals: {castError}" onretry={loadCast} />
    {:else if cast === null}
      <p>Loading…</p>
    {:else}
      <ul class="cast">
        {#each cast as s, i (s.key)}
          <li style:--i={i}>
            <span class="mug"><Avatar kind={s.key} label={s.character} /></span>
            <strong>{s.character}</strong>
            <em>{s.name}</em>
            <span>{s.blurb}</span>
          </li>
        {/each}
      </ul>
    {/if}
    {#if cast || castError}
      <label class="option">
        <input type="checkbox" bind:checked={carry} /> Keep stacks between hands
        <small>Win big or play short; anyone under 10bb is topped up.</small>
      </label>
      <button type="button" class="big" disabled={busy} onclick={() => run(() => api.play(carry))}>Deal me in!</button>
    {/if}
    <p><a href={href('review')}>Review your past hands →</a></p>
  </section>
{:else if table}
  <header class="session">
    <span class="pill">Hand {game.hands_played + (game.hand.finished ? 0 : 1)}</span>
    <span class="pill" class:won={game.net_bb > 0} class:lost={game.net_bb < 0} aria-label="Session result"
      >{game.net_bb > 0 ? '+' : ''}{game.net_bb}bb</span
    >
    {#if game.carry}<span class="pill">Stacks carry over</span>{/if}
    <button type="button" class="mute" aria-pressed={sound} aria-label="Sound" onclick={toggleSound}
      >{sound ? '🔊' : '🔇'}</button
    >
    <button type="button" class="link" onclick={leave}>Leave table</button>
  </header>

  <div class="stage">
    <PokerTable hand={table} seats={game.seats} {sweep} {tick} />
    {#if over}
      {#key game.hands_played}
        <div class="banner" class:win={net > 0} class:loss={net < 0}>
          <h2>{outcome}</h2>
        </div>
        {#if net > 0}<div class="winflash" aria-hidden="true"></div>{/if}
        {#if net >= BIG_WIN}<Confetti />{/if}
      {/key}
    {/if}
  </div>

  <div class="controls" class:done={over} tabindex="-1" bind:this={controls}>
    {#if !settled}
      <button type="button" class="skip" onclick={skip}>Skip ▸▸ <kbd>Space</kbd></button>
    {:else if yourTurn && game.legal}
      <ActionBar
        legal={game.legal}
        pot={game.hand.pot}
        currentBet={game.hand.bets[0]}
        disabled={busy}
        onact={(kind, to) => run(() => api.act(game!.id, kind, to))}
      />
      <label class="coach-toggle"><input type="checkbox" checked={showCoach} onchange={toggleCoach} /> Coach</label>
      {#if showCoach && coach}
        <p class="coach" aria-label="Coach">
          {#if coach.chart}First in: the chart says <strong>{coach.chart.toLowerCase()}</strong>.
          {:else if coach.need !== null}Price: call {coach.to_call_bb}bb into {coach.pot_bb}bb needs
            <strong>{Math.round(coach.need * 100)}%</strong>.{/if}
          Your equity against {coach.opponents === 1 ? "the bot's likely range" : `${coach.opponents} bots' likely ranges`}:
          <strong>{Math.round(coach.equity * 100)}%</strong>.
        </p>
      {/if}
    {:else if over}
      <button type="button" class="big next" disabled={busy} onclick={() => run(() => api.nextHand(game!.id))}
        >Next hand <kbd>N</kbd></button
      >
    {/if}
  </div>

  {#if over}
    <section class="result" aria-label="Hand result">
      <h3>Your decisions</h3>
      <DecisionList decisions={game.decisions} />
      <p class="note">
        Graded against the bots' likely hands, narrowed by every action they took. Bets and raises
        assume no more betting after a call, so treat the numbers as estimates.
      </p>
    </section>
  {/if}

  <details class="log">
    <summary>Action log</summary>
    <ol>
      {#each log as a, i (i)}<li><span class="street">{a.street}</span> {describe(a, names)}</li>{/each}
    </ol>
  </details>
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
  .cast {
    list-style: none;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
    gap: 0.9rem;
    margin: 1.2rem 0;
  }
  .cast li {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0.15rem;
    padding: 0.9rem 0.8rem;
    border-radius: 1.1rem;
    border: 3px solid var(--ink);
    background: var(--surface);
    box-shadow: 0 5px 0 var(--ink);
    animation: rise 0.4s cubic-bezier(0.3, 1.5, 0.5, 1) backwards;
    animation-delay: calc(var(--i) * 70ms);
    transition: transform 0.15s;
  }
  .cast li:hover {
    transform: translateY(-4px) rotate(-1.5deg);
  }
  .cast li:nth-child(1) { background: #dfe4ef; }
  .cast li:nth-child(2) { background: #cfe3ff; }
  .cast li:nth-child(3) { background: #ffdcc4; }
  .cast li:nth-child(4) { background: #c9f5ee; }
  .cast li:nth-child(5) { background: #ffd0cf; }
  .cast li {
    color: #2a1a3a;
  }
  .mug {
    width: 4.6rem;
    height: 4.6rem;
  }
  .cast strong {
    font-size: 1.15rem;
  }
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
  .cast span:last-child {
    font-size: 0.85rem;
  }
  .big {
    padding: 0.8rem 2rem;
    border-radius: 1rem;
    border: 3px solid var(--ink);
    background: linear-gradient(#ffe94d, #ffb02e);
    color: #2a1a3a;
    font-size: 1.25rem;
    font-weight: 900;
    box-shadow: 0 6px 0 var(--ink);
    transition:
      transform 0.08s,
      box-shadow 0.08s;
    animation: wiggle 2.4s ease-in-out infinite;
  }
  .big:hover:not(:disabled) {
    border-color: var(--ink);
    filter: brightness(1.06);
  }
  .big:active:not(:disabled) {
    transform: translateY(4px);
    box-shadow: 0 2px 0 var(--ink);
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
    border: 2px solid var(--ink);
    background: var(--surface);
    font-weight: 800;
    box-shadow: 0 3px 0 var(--ink);
    font-variant-numeric: tabular-nums;
  }
  .pill.won {
    background: #a8f0b4;
    color: #2a1a3a;
  }
  .pill.lost {
    background: #ffb3ad;
    color: #2a1a3a;
  }
  .option {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.2rem 0.5rem;
    margin-bottom: 1rem;
    font-weight: 800;
  }
  .option small {
    font-weight: 400;
    color: var(--muted);
  }
  .mute {
    margin-left: auto;
    padding: 0.1rem 0.6rem;
    border-radius: 999px;
  }
  .link {
    border: none;
    box-shadow: none;
    background: none;
    padding: 0;
    color: var(--muted);
    text-decoration: underline;
  }
  .stage {
    position: relative;
  }
  .banner {
    position: absolute;
    left: 50%;
    top: 61%;
    z-index: 7;
    transform: translate(-50%, -50%) rotate(-3deg);
    padding: 0.5rem 1.6rem;
    border-radius: 1.1rem;
    border: 3px solid #2a1a3a;
    background: #fff;
    color: #2a1a3a;
    box-shadow: 0 6px 0 #2a1a3a;
    white-space: nowrap;
    pointer-events: none;
    animation: slam 0.55s cubic-bezier(0.3, 1.6, 0.5, 1) 0.9s backwards;
  }
  .banner h2 {
    margin: 0;
    font-size: clamp(1.1rem, 4.5vw, 2rem);
    font-weight: 900;
  }
  .banner.win {
    background: linear-gradient(#ffe94d, #ffb02e);
  }
  .banner.loss {
    background: #ffd0cf;
  }
  .winflash {
    position: absolute;
    inset: 0;
    z-index: 6;
    border-radius: 1.6rem;
    background: radial-gradient(circle, #fff 0, #ffe94d 40%, transparent 75%);
    pointer-events: none;
    opacity: 0;
    animation: flash 0.7s ease-out 0.9s;
  }
  .controls {
    min-height: 7.5rem;
    margin-top: 0.9rem;
  }
  .controls:focus {
    outline: none;
  }
  .controls.done {
    min-height: 0;
    margin-bottom: 1rem;
  }
  .skip {
    border: 2px solid var(--ink);
    border-radius: 999px;
    font-weight: 800;
    box-shadow: 0 3px 0 var(--ink);
  }
  .next {
    animation: none;
    font-size: 1.1rem;
    padding: 0.6rem 1.6rem;
  }
  kbd {
    font-size: 0.7rem;
    opacity: 0.7;
  }
  .coach-toggle {
    display: inline-flex;
    gap: 0.4rem;
    margin-top: 0.7rem;
    font-weight: 700;
  }
  .coach {
    padding: 0.6rem 0.9rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: 2px solid var(--ink);
    box-shadow: 0 3px 0 var(--ink);
  }
  .result {
    margin-top: 0.5rem;
    padding: 0.4rem 1.2rem 1rem;
    border-radius: 1.1rem;
    background: var(--surface);
    border: 2px solid var(--ink);
    box-shadow: 0 4px 0 var(--ink);
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
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(1.2rem) scale(0.9);
    }
  }
  @keyframes wiggle {
    0%,
    86%,
    100% {
      rotate: 0deg;
    }
    90% {
      rotate: -2.5deg;
    }
    95% {
      rotate: 2.5deg;
    }
  }
  @keyframes slam {
    from {
      opacity: 0;
      transform: translate(-50%, -50%) rotate(-14deg) scale(2.6);
    }
  }
  @keyframes flash {
    0% {
      opacity: 0.9;
    }
    100% {
      opacity: 0;
    }
  }
  @media (pointer: coarse) {
    kbd {
      display: none;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .cast li,
    .big,
    .banner,
    .winflash {
      animation: none;
    }
  }
</style>
