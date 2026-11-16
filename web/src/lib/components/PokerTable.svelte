<script lang="ts">
  import type { HandView } from '../api'
  import { toBb } from '../play'
  import PlayingCard from './PlayingCard.svelte'

  let { hand, names }: { hand: HandView; names: [string, string] } = $props()

  const seat = (player: number) => ({
    name: names[player],
    cards: hand.hole[player],
    behind: toBb(hand.behind[player]),
    bet: toBb(hand.bets[player]),
    button: hand.button === player,
    acting: hand.current === player,
    net: hand.net ? toBb(hand.net[player]) : null,
  })
  const villain = $derived(seat(1))
  const hero = $derived(seat(0))
</script>

<section class="table" aria-label="Poker table">
  {#each [villain, hero] as s, i (i)}
    <div class="seat" class:acting={s.acting} class:top={i === 0}>
      <div class="who">
        <strong>{s.name}</strong>
        {#if s.button}<span class="dealer" title="Dealer button (small blind)">D</span>{/if}
        <span class="stack">{s.behind}bb</span>
        {#if s.net !== null}
          <span class="net" class:won={s.net > 0} class:lost={s.net < 0}
            >{s.net > 0 ? '+' : ''}{s.net}bb</span
          >
        {/if}
      </div>
      <div class="cards">
        {#if s.cards}
          {#each s.cards as code, k (code)}<PlayingCard {code} order={k} />{/each}
        {:else}
          <span class="back" aria-label="Hidden card"></span><span class="back" aria-label="Hidden card"
          ></span>
        {/if}
      </div>
      {#if s.bet}<span class="chips" aria-label="{s.name} bet">{s.bet}bb</span>{/if}
    </div>
    {#if i === 0}
      <div class="middle">
        <div class="board" aria-label="Board">
          {#each hand.board as code, k (code)}<PlayingCard {code} order={k} />{/each}
          {#each { length: 5 - hand.board.length } as _, k (k)}<span class="slot"></span>{/each}
        </div>
        <span class="pot" aria-label="Pot">Pot {toBb(hand.pot)}bb</span>
      </div>
    {/if}
  {/each}
</section>

<style>
  .table {
    display: grid;
    gap: 0.9rem;
    padding: 1.2rem;
    border-radius: 1.5rem;
    background: radial-gradient(ellipse at center, var(--felt-light), var(--felt));
    color: var(--felt-text);
    border: 6px solid #3b2a1a;
    box-shadow: inset 0 0 30px rgb(0 0 0 / 0.35);
  }
  .seat {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 0.5rem 0.75rem;
    border-radius: 0.9rem;
    transition: box-shadow 0.2s;
  }
  .seat.acting {
    box-shadow: 0 0 0 2px #f2b544;
  }
  .who {
    display: flex;
    flex-direction: column;
    min-width: 7rem;
  }
  .stack {
    opacity: 0.85;
    font-variant-numeric: tabular-nums;
  }
  .dealer {
    display: inline-grid;
    place-items: center;
    width: 1.4rem;
    height: 1.4rem;
    border-radius: 50%;
    background: #fff;
    color: #111;
    font-size: 0.75rem;
    font-weight: 800;
  }
  .net.won {
    color: #8ff0b4;
    font-weight: 700;
  }
  .net.lost {
    color: #ffb3ad;
    font-weight: 700;
  }
  .cards {
    display: flex;
    gap: 0.35rem;
  }
  .back,
  .slot {
    width: var(--card-w, 3.4rem);
    height: calc(var(--card-w, 3.4rem) * 1.4);
    border-radius: 0.45rem;
  }
  .back {
    background: repeating-linear-gradient(45deg, #b8322b 0 6px, #8e231d 6px 12px);
    border: 2px solid #fff;
  }
  .slot {
    border: 2px dashed rgb(255 255 255 / 0.18);
  }
  .chips {
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    background: #f2b544;
    color: #1d1505;
    font-weight: 700;
  }
  .middle {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  .board {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    justify-content: center;
  }
  .pot {
    font-weight: 700;
    background: rgb(0 0 0 / 0.25);
    padding: 0.2rem 0.8rem;
    border-radius: 999px;
  }
  @media (max-width: 520px) {
    .table {
      --card-w: 2.7rem;
      padding: 0.8rem;
    }
  }
</style>
