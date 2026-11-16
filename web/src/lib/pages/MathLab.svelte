<script lang="ts">
  import { api, type DrillMeta } from '../api'
  import DrillRunner from '../components/DrillRunner.svelte'
  import { TIER_NAMES } from '../format'
  import { href } from '../router.svelte'

  let { selected = undefined }: { selected?: string } = $props()

  let drills = $state<DrillMeta[]>([])
  let error = $state<string | null>(null)

  $effect(() => {
    api.drills().then(
      (list) => (drills = list),
      (e: Error) => (error = e.message),
    )
  })

  const tiers = $derived(
    [...new Set(drills.map((d) => d.tier))]
      .sort((a, b) => a - b)
      .map((tier) => ({ tier, drills: drills.filter((d) => d.tier === tier) })),
  )
  const active = $derived(
    selected === 'mixed' ? drills : drills.filter((d) => d.key === selected),
  )
</script>

{#if error}
  <p role="alert">Could not load drills: {error}</p>
{:else if selected}
  <nav class="crumbs"><a href={href('math-lab')}>← All drills</a></nav>
  {#if active.length}
    <DrillRunner drills={active} />
  {:else if drills.length}
    <p>Unknown drill “{selected}”.</p>
  {/if}
{:else}
  <h1>Math Lab</h1>
  <p class="lead">
    Short, fast drills on the numbers behind every decision. Answers are computed by the engine,
    and every one comes with the working.
  </p>
  <a class="mixed" href={href('math-lab', 'mixed')}>Start a mixed session</a>
  {#each tiers as group (group.tier)}
    <h2>Tier {group.tier} · {TIER_NAMES[group.tier]}</h2>
    <div class="grid">
      {#each group.drills as drill (drill.key)}
        <a class="tile" href={href('math-lab', drill.key)}>
          <strong>{drill.title}</strong>
          <span>{drill.description}</span>
        </a>
      {/each}
    </div>
  {/each}
{/if}

<style>
  .lead {
    color: var(--muted);
    max-width: 40rem;
  }
  .mixed {
    display: inline-block;
    margin: 0.5rem 0 1rem;
    padding: 0.6rem 1.1rem;
    border-radius: 0.6rem;
    background: var(--accent);
    color: var(--on-accent);
    font-weight: 600;
    text-decoration: none;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 0.75rem;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    padding: 0.9rem 1rem;
    border-radius: 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
    transition: border-color 0.15s;
  }
  .tile:hover {
    border-color: var(--accent);
  }
  .tile span {
    font-size: 0.9rem;
    color: var(--muted);
  }
  .crumbs {
    margin-bottom: 1rem;
  }
</style>
