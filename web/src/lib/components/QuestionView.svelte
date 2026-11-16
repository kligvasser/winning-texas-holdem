<script lang="ts">
  import type { Question } from '../api'
  import CardRow from './CardRow.svelte'

  let { question }: { question: Question } = $props()
  const p = $derived(question.payload)
</script>

<section class="felt" aria-label="Situation">
  {#if p.pot !== undefined}
    <div class="chips">
      <span>Pot <strong>{p.pot}</strong></span>
      {#if p.bet !== undefined}<span>Bet <strong>{p.bet}</strong></span>{/if}
    </div>
  {/if}
  {#if p.board}
    <CardRow label="Board" cards={p.board} />
  {/if}
  <div class="hands">
    {#if p.hole}<CardRow label="You" cards={p.hole} />{/if}
    {#if p.villain}<CardRow label="Villain" cards={p.villain} />{/if}
    {#each p.players ?? [] as hand, i (i)}
      <CardRow label="Player {i + 1}" cards={hand} />
    {/each}
  </div>
</section>
<p class="prompt">{question.prompt}</p>

<style>
  .felt {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.25rem;
    border-radius: 1rem;
    background: radial-gradient(ellipse at center, var(--felt-light), var(--felt));
    color: var(--felt-text);
    min-height: 3rem;
  }
  .felt:empty {
    display: none;
  }
  .hands {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
  }
  .hands:empty {
    display: none;
  }
  .chips {
    display: flex;
    gap: 1rem;
    font-size: 0.95rem;
  }
  .chips span {
    background: rgb(0 0 0 / 0.25);
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
  }
  .prompt {
    font-size: 1.15rem;
    font-weight: 600;
    margin: 1rem 0 0.75rem;
  }
</style>
