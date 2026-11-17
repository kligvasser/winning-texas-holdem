<script lang="ts">
  import type { PlayStyle, TableView } from '../api'
  import { shout, signedBb, toBb } from '../play'
  import Avatar from './Avatar.svelte'
  import ChipStack from './ChipStack.svelte'
  import PlayingCard from './PlayingCard.svelte'

  let {
    hand,
    seats,
    sweep = null,
    tick = 0,
  }: {
    hand: TableView
    seats: PlayStyle[]
    /** The bets that were just pushed into the pot, to animate them on their way. */
    sweep?: number[] | null
    /** Changes with every new table position, so one-shot animations play again. */
    tick?: number
  } = $props()

  const last = $derived(hand.last)
  const allIn = $derived(
    !hand.finished && ['call', 'bet', 'raise'].includes(last.kind) && hand.behind[last.player] === 0,
  )
  /** Chips already swept into the middle (the pot without this street's bets). */
  const collected = $derived(hand.pot - hand.bets.reduce((a, b) => a + b, 0))
  const view = $derived(
    seats.map((seat, i) => ({
      ...seat,
      index: i,
      you: i === 0,
      cards: hand.hole[i],
      folded: hand.folded[i],
      acting: hand.current === i,
      winner: hand.finished && hand.winners.includes(i),
      net: hand.net ? hand.net[i] : null,
      said: !hand.finished && last.player === i ? shout(last, allIn) : null,
    })),
  )
</script>

<section class="table" class:over={hand.finished} aria-label="Poker table">
  <div class="felt" aria-hidden="true"></div>

  <div class="middle">
    <div class="board" aria-label="Board">
      {#each hand.board as code, k (code)}<PlayingCard {code} order={k % 3} />{/each}
      {#each { length: 5 - hand.board.length } as _, k (k)}<span class="slot"></span>{/each}
    </div>
    <div class="pot" aria-label="Pot">
      {#if collected > 0 && !hand.finished}
        <ChipStack chips={collected} label="Chips in the pot" text={false} />
      {/if}
      <strong>Pot {toBb(hand.pot)}bb</strong>
    </div>
  </div>

  {#each view as s (s.index)}
    <div
      class="seat slot-{s.index}"
      class:you={s.you}
      class:acting={s.acting}
      class:folded={s.folded}
      class:winner={s.winner}
      aria-label="{s.character}{s.folded ? ' (folded)' : ''}"
      aria-current={s.acting ? 'true' : undefined}
      role="group"
    >
      {#if s.said}
        {#key tick}<span class="said k-{last.kind}" class:allin={allIn}>{s.said}</span>{/key}
      {/if}
      <div class="face" title={s.blurb ? `${s.name}: ${s.blurb}` : undefined}>
        {#if s.winner}<span class="rays" aria-hidden="true"></span>{/if}
        <Avatar kind={s.key} mood={s.folded ? 'out' : s.winner ? 'happy' : 'idle'} label={s.name} />
        {#if hand.button === s.index}<span class="dealer" title="Dealer button">D</span>{/if}
      </div>
      <div class="cards">
        {#if s.cards && !(s.folded && !s.you && !hand.finished)}
          {#each s.cards as code, k (code)}<PlayingCard {code} order={k} />{/each}
        {:else if !s.folded}
          <span class="back" aria-label="Hidden card"></span><span class="back" aria-label="Hidden card"
          ></span>
        {/if}
      </div>
      <div class="plate">
        <span class="name">{s.character} <em>{hand.positions[s.index]}</em></span>
        <span class="chips-left">{toBb(hand.behind[s.index])}bb</span>
        {#if hand.made[s.index] && !s.folded}<span class="made">{hand.made[s.index]}</span>{/if}
        {#if s.net !== null && s.net !== 0}
          <span class="net" class:won={s.net > 0} class:lost={s.net < 0}>{signedBb(s.net)}</span>
        {/if}
      </div>
    </div>
    {#if hand.bets[s.index]}
      <div class="bet slot-{s.index}">
        <ChipStack chips={hand.bets[s.index]} label="{s.character} bet" />
      </div>
    {/if}
  {/each}

  {#key tick}
    {#if sweep}
      {#each sweep as chips, i (i)}
        {#if chips}
          <div class="fly in slot-{i}" aria-hidden="true"><ChipStack {chips} label="" text={false} /></div>
        {/if}
      {/each}
    {/if}
    {#if hand.finished}
      {#each hand.winners as w (w)}
        <div class="fly out slot-{w}" aria-hidden="true">
          <ChipStack chips={hand.pot / hand.winners.length} label="" text={false} />
        </div>
      {/each}
    {/if}
    {#if allIn}
      <div class="flash" aria-hidden="true"></div>
      <div class="burst" role="status">ALL IN!</div>
    {/if}
  {/key}
</section>

<style>
  .table {
    --ink: #2a1a3a;
    --card-w: 3.1rem;
    position: relative;
    aspect-ratio: 3 / 2;
    border-radius: 1.6rem;
    border: 3px solid var(--ink);
    background:
      radial-gradient(circle at 12% 18%, #fff 0 2.2rem, transparent 2.3rem),
      radial-gradient(circle at 17% 15%, #fff 0 1.6rem, transparent 1.7rem),
      radial-gradient(circle at 84% 12%, #fff 0 1.9rem, transparent 2rem),
      radial-gradient(circle at 89% 15%, #fff 0 1.3rem, transparent 1.4rem),
      linear-gradient(#5ec8ff 0 62%, #8be06a 62% 100%);
    box-shadow: 0 6px 0 var(--ink);
    overflow: hidden;
    color: #fff;
    user-select: none;
  }
  .felt {
    position: absolute;
    inset: 15% 7% 17%;
    border-radius: 50%;
    border: 0.9rem solid #b5722f;
    outline: 3px solid var(--ink);
    background: radial-gradient(ellipse at 50% 40%, #3fd07a, #1c9a52 70%, #15803f);
    box-shadow:
      inset 0 0 0 3px var(--ink),
      inset 0 0 0 0.6rem rgb(255 255 255 / 0.12),
      0 0.55rem 0 var(--ink);
  }
  .middle {
    position: absolute;
    left: 50%;
    top: 45%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
  }
  .board {
    display: flex;
    gap: 0.3rem;
  }
  .slot {
    width: var(--card-w);
    height: calc(var(--card-w) * 1.4);
    border-radius: 0.45rem;
    border: 2px dashed rgb(255 255 255 / 0.35);
  }
  .pot {
    display: flex;
    align-items: flex-end;
    gap: 0.4rem;
  }
  .pot strong {
    padding: 0.1rem 0.8rem;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: #ffc928;
    color: var(--ink);
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  /* Seats sit around the table; --x/--y place the seat, --bx/--by its bet. */
  .slot-0 { --x: 50%; --y: 84%; --bx: 50%; --by: 66%; }
  .slot-1 { --x: 9%; --y: 66%; --bx: 25%; --by: 60%; }
  .slot-2 { --x: 13%; --y: 23%; --bx: 28%; --by: 33%; }
  .slot-3 { --x: 50%; --y: 12%; --bx: 50%; --by: 27%; }
  .slot-4 { --x: 87%; --y: 23%; --bx: 72%; --by: 33%; }
  .slot-5 { --x: 91%; --y: 66%; --bx: 75%; --by: 60%; }

  .seat {
    position: absolute;
    left: var(--x);
    top: var(--y);
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    --card-w: 2.1rem;
    transition: opacity 0.3s;
  }
  .seat.you {
    --card-w: 3.1rem;
    flex-direction: row;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: center;
    width: 15rem;
  }
  .face {
    position: relative;
    isolation: isolate;
    width: 4.7rem;
    height: 4.7rem;
  }
  .acting .face {
    animation: hop 0.55s ease-in-out infinite alternate;
  }
  .acting .face::before {
    content: '';
    position: absolute;
    inset: -0.5rem;
    z-index: -1;
    border-radius: 50%;
    background: radial-gradient(circle, rgb(255 233 77 / 0.95) 35%, transparent 70%);
    animation: pulse 0.9s ease-in-out infinite alternate;
  }
  .rays {
    position: absolute;
    inset: -1.3rem;
    z-index: -1;
    border-radius: 50%;
    background: repeating-conic-gradient(#ffe94d 0 12deg, transparent 12deg 30deg);
    mask: radial-gradient(circle, #000 30%, transparent 70%);
    animation: spin 5s linear infinite;
  }
  .dealer {
    position: absolute;
    right: -0.5rem;
    top: -0.3rem;
    display: grid;
    place-items: center;
    width: 1.45rem;
    height: 1.45rem;
    border-radius: 50%;
    border: 2px solid var(--ink);
    background: #fff;
    color: var(--ink);
    font-size: 0.75rem;
    font-weight: 900;
    box-shadow: 0 2px 0 var(--ink);
  }
  .cards {
    display: flex;
    gap: 0.15rem;
    margin-top: -1.1rem;
    min-height: 1.1rem;
    z-index: 1;
  }
  .you .cards {
    margin-top: 0;
    gap: 0.3rem;
  }
  .back {
    width: var(--card-w);
    height: calc(var(--card-w) * 1.4);
    border-radius: 0.3rem;
    border: 2px solid var(--ink);
    background:
      radial-gradient(circle, #ffc928 0 18%, transparent 20%),
      repeating-linear-gradient(45deg, #e5484d 0 5px, #c2333a 5px 10px);
    box-shadow: 0 2px 0 var(--ink);
    animation: deal-in 0.3s ease-out backwards;
  }
  .back:first-child {
    transform: rotate(-7deg);
  }
  .back:last-child {
    transform: rotate(7deg);
  }
  .plate {
    display: grid;
    justify-items: center;
    margin-top: 0.15rem;
    padding: 0.1rem 0.6rem 0.15rem;
    border-radius: 0.7rem;
    border: 2px solid var(--ink);
    background: #fff;
    color: var(--ink);
    line-height: 1.2;
    box-shadow: 0 3px 0 var(--ink);
    z-index: 2;
    white-space: nowrap;
  }
  .you .plate {
    flex-basis: 100%;
    max-width: max-content;
    background: #ffe94d;
  }
  .name {
    font-weight: 800;
    font-size: 0.82rem;
  }
  .name em {
    font-style: normal;
    font-size: 0.65rem;
    padding: 0 0.3rem;
    border-radius: 0.3rem;
    background: var(--ink);
    color: #fff;
  }
  .chips-left {
    font-size: 0.78rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .made {
    font-size: 0.68rem;
    font-weight: 800;
    color: #b3261e;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .folded .plate {
    background: #e3e6ef;
    color: #6b6880;
  }
  .said {
    position: absolute;
    bottom: 100%;
    z-index: 3;
    padding: 0.1rem 0.6rem;
    border-radius: 0.8rem;
    border: 2px solid var(--ink);
    background: #fff;
    color: var(--ink);
    font-weight: 800;
    font-size: 0.8rem;
    white-space: nowrap;
    box-shadow: 0 3px 0 var(--ink);
    animation: pop 0.3s cubic-bezier(0.3, 1.6, 0.5, 1) backwards;
  }
  .slot-3 .said,
  .slot-2 .said,
  .slot-4 .said {
    bottom: auto;
    top: 2.2rem;
    left: 100%;
  }
  .slot-4 .said {
    left: auto;
    right: 100%;
  }
  .you .said {
    bottom: 100%;
  }
  .k-fold {
    background: #d7dbe6;
  }
  .k-call,
  .k-check {
    background: #a8f0b4;
  }
  .k-bet,
  .k-raise {
    background: #ffc928;
  }
  .said.allin {
    background: #e5484d;
    color: #fff;
  }
  .net {
    margin: 0.1rem 0;
    padding: 0 0.6rem;
    border-radius: 999px;
    border: 2px solid var(--ink);
    font-weight: 900;
    font-size: 0.85rem;
    animation: pop 0.4s cubic-bezier(0.3, 1.6, 0.5, 1) 0.5s backwards;
  }
  .net.won {
    background: #ffe94d;
    color: var(--ink);
  }
  .net.lost {
    background: #e5484d;
    color: #fff;
  }
  .bet,
  .fly {
    position: absolute;
    left: var(--bx);
    top: var(--by);
    transform: translate(-50%, -50%);
    z-index: 2;
  }
  .fly {
    pointer-events: none;
  }
  .fly.in {
    animation: to-pot 0.5s ease-in forwards;
  }
  .fly.out {
    left: 50%;
    top: 58%;
    animation: to-seat 0.7s cubic-bezier(0.5, 0, 0.3, 1) 0.25s forwards;
  }
  .flash {
    position: absolute;
    inset: 0;
    z-index: 5;
    background: radial-gradient(circle, #fff 0, #ffe94d 45%, transparent 75%);
    pointer-events: none;
    opacity: 0;
    animation: flash 0.6s ease-out;
  }
  .over .felt {
    animation: glow 0.7s ease-out;
  }
  .burst {
    position: absolute;
    left: 50%;
    top: 45%;
    z-index: 6;
    display: grid;
    place-items: center;
    width: 11rem;
    height: 11rem;
    background: #e5484d;
    color: #fff;
    font-size: 1.7rem;
    font-weight: 900;
    letter-spacing: 0.03em;
    text-shadow:
      2px 2px 0 var(--ink),
      -2px 2px 0 var(--ink),
      2px -2px 0 var(--ink),
      -2px -2px 0 var(--ink);
    clip-path: polygon(
      50% 0, 61% 18%, 79% 7%, 80% 28%, 100% 30%, 87% 47%, 100% 65%, 80% 68%, 82% 90%, 62% 80%,
      50% 100%, 38% 80%, 18% 90%, 20% 68%, 0 65%, 13% 47%, 0 30%, 20% 28%, 21% 7%, 39% 18%
    );
    pointer-events: none;
    opacity: 0;
    transform: translate(-50%, -50%);
    animation: burst 1.1s cubic-bezier(0.3, 1.5, 0.5, 1);
  }

  @keyframes hop {
    to {
      transform: translateY(-0.35rem);
    }
  }
  @keyframes pulse {
    from {
      opacity: 0.45;
      transform: scale(0.9);
    }
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: scale(0.3);
    }
  }
  @keyframes deal-in {
    from {
      opacity: 0;
      translate: 0 -1rem;
    }
  }
  @keyframes to-pot {
    to {
      left: 50%;
      top: 58%;
      opacity: 0;
    }
  }
  @keyframes to-seat {
    from {
      opacity: 1;
    }
    to {
      left: var(--x);
      top: var(--y);
      opacity: 0;
    }
  }
  @keyframes flash {
    0% {
      opacity: 0.95;
    }
    100% {
      opacity: 0;
    }
  }
  @keyframes glow {
    0% {
      filter: brightness(1.9) saturate(1.4);
    }
  }
  @keyframes burst {
    0% {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0.2) rotate(-25deg);
    }
    25%,
    75% {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1) rotate(-8deg);
    }
    100% {
      opacity: 0;
      transform: translate(-50%, -50%) scale(1.4) rotate(-8deg);
    }
  }

  @media (max-width: 640px) {
    .table {
      --card-w: 2.3rem;
      aspect-ratio: 3 / 4.8;
    }
    .felt {
      inset: 15% 9% 17%;
      border-width: 0.6rem;
    }
    .middle {
      top: 48%;
    }
    .slot-0 { --x: 50%; --y: 84%; --bx: 50%; --by: 69%; }
    .slot-1 { --x: 15%; --y: 64%; --bx: 36%; --by: 59%; }
    .slot-2 { --x: 15%; --y: 30%; --bx: 36%; --by: 34%; }
    .slot-3 { --x: 50%; --y: 16%; --bx: 50%; --by: 29%; }
    .slot-4 { --x: 85%; --y: 30%; --bx: 64%; --by: 34%; }
    .slot-5 { --x: 85%; --y: 64%; --bx: 64%; --by: 59%; }
    .seat {
      --card-w: 1.5rem;
    }
    .seat.you {
      --card-w: 2.5rem;
      width: 12rem;
    }
    .face {
      width: 3rem;
      height: 3rem;
    }
    .name {
      font-size: 0.72rem;
    }
    .plate {
      padding: 0 0.4rem 0.1rem;
    }
    .slot-2 .said,
    .slot-3 .said,
    .slot-4 .said {
      left: auto;
      right: auto;
      top: 100%;
    }
    .burst {
      width: 9rem;
      height: 9rem;
      font-size: 1.4rem;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .table *,
    .table *::before {
      animation: none !important;
    }
    .fly {
      display: none;
    }
  }
</style>
