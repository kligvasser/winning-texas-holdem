<script lang="ts">
  import type { Question } from '../api'
  import CardRow from './CardRow.svelte'

  let { question }: { question: Question } = $props()
  const p = $derived(question.payload)
</script>

<section class="felt" aria-label="Situation">
  {#if p.facts?.length}
    <div class="chips">
      {#each p.facts as fact (fact.label)}<span>{fact.label} <strong>{fact.value}</strong></span>{/each}
    </div>
  {/if}
  {#if typeof p.position === 'string'}
    <div class="chips"><span>Position <strong>{p.position}</strong></span></div>
  {/if}
  {#if p.pot !== undefined}
    <div class="chips">
      <span>Pot <strong>{p.pot}</strong></span>
      {#if p.bet !== undefined}<span>Bet <strong>{p.bet}</strong></span>{/if}
    </div>
  {/if}
  {#if p.lines?.length}
    <ol class="lines" aria-label="Action so far">
      {#each p.lines as line, i (i)}<li>{line}</li>{/each}
    </ol>
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
    padding: 1.7rem;
    border-radius: 1.6rem;
    border: 3px solid var(--ink);
    box-shadow:
      inset 0 0 0 0.5rem var(--wood),
      inset 0 0 0 calc(0.5rem + 3px) var(--ink),
      0 6px 0 var(--ink);
    background: radial-gradient(ellipse at 50% 40%, #3fd07a, #1c9a52 70%, #15803f);
    color: #fff;
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
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    font-size: 0.95rem;
  }
  .chips span {
    background: var(--sun);
    color: var(--on-bright);
    border: 2px solid #2a1a3a;
    box-shadow: 0 3px 0 #2a1a3a;
    padding: 0.1rem 0.8rem;
    border-radius: 999px;
  }
  .lines {
    margin: 0;
    padding: 0.6rem 0.9rem 0.6rem 2rem;
    border-radius: 0.6rem;
    background: rgb(0 0 0 / 0.22);
    font-size: 0.9rem;
    line-height: 1.5;
  }
  .prompt {
    font-size: 1.2rem;
    font-weight: 800;
    margin: 1rem 0 0.75rem;
  }
</style>
