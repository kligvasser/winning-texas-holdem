<script lang="ts">
  import type { ReviewedDecision } from '../api'

  let { decisions }: { decisions: ReviewedDecision[] } = $props()
  const LABEL = { good: 'Good', leak: 'Small leak', mistake: 'Mistake', info: 'Not graded' }
</script>

{#if decisions.length}
  <ol class="decisions">
    {#each decisions as d (d.index)}
      <li class="v-{d.verdict}">
        <span class="badge">{LABEL[d.verdict]}</span>
        <strong>{d.street}: you {d.action}{d.amount_bb ? ` ${d.amount_bb}bb` : ''}</strong>
        {#if d.loss_bb > 0}<span class="loss">−{d.loss_bb}bb</span>{/if}
        <p>{d.note}</p>
      </li>
    {/each}
  </ol>
{:else}
  <p class="muted">You made no decisions this hand.</p>
{/if}

<style>
  .decisions {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }
  li {
    padding: 0.6rem 0.8rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: var(--line);
    border-left: 0.6rem solid var(--border);
    box-shadow: var(--drop-sm);
  }
  li p {
    margin: 0.3rem 0 0;
    font-size: 0.9rem;
    color: var(--muted);
  }
  .badge {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 900;
    margin-right: 0.4rem;
  }
  .v-good {
    border-left-color: var(--good);
  }
  .v-leak {
    border-left-color: var(--sun-deep);
  }
  .v-mistake {
    border-left-color: var(--bad);
  }
  .v-mistake .badge,
  .loss {
    color: var(--bad);
    font-weight: 700;
  }
  .loss {
    margin-left: 0.4rem;
  }
  .muted {
    color: var(--muted);
  }
</style>
