<script lang="ts">
  import { api, type DrillMeta } from '../api'
  import DrillRunner from '../components/DrillRunner.svelte'
  import { groupByTier, TIER_NAMES } from '../format'
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
  <div class="starts">
    <a class="mixed" href={href('math-lab', 'mixed')}>Start a mixed session</a>
    <a class="mixed speed" href={href('speed', 'mixed')}>⚡ 60-second speed round</a>
  </div>
  {#each groupByTier(drills) as [tier, tierDrills] (tier)}
    <h2>Tier {tier} · {TIER_NAMES[tier]}</h2>
    <div class="grid">
      {#each tierDrills as drill (drill.key)}
        <a class="tile" href={href('math-lab', drill.key)}>
          <strong>{drill.title}{#if drill.speed}<span class="bolt" title="Has a speed round"> ⚡</span>{/if}</strong>
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
  .starts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .mixed.speed {
    background: linear-gradient(#ffe94d, var(--sun-deep));
  }
  .mixed:active {
    transform: translateY(3px);
    box-shadow: none;
  }
  .mixed {
    display: inline-block;
    margin: 0.5rem 0 1rem;
    padding: 0.6rem 1.1rem;
    border-radius: 0.9rem;
    background: linear-gradient(var(--mint), #3fc66b);
    color: var(--on-bright);
    border: var(--line);
    box-shadow: var(--drop-sm);
    font-weight: 800;
    text-decoration: none;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    padding: 0.9rem 1rem;
    border-radius: 1.1rem;
    background: var(--surface);
    border: var(--line);
    box-shadow: var(--drop);
    color: inherit;
    font-weight: 400;
    text-decoration: none;
    transition:
      transform 0.12s ease,
      box-shadow 0.12s ease;
  }
  .tile:hover {
    transform: translateY(-3px);
    box-shadow: 0 7px 0 var(--ink);
  }
  .tile strong {
    font-weight: 900;
  }
  .bolt {
    font-size: 0.9rem;
  }
  .tile > span {
    font-size: 0.9rem;
    color: var(--muted);
  }
  .crumbs {
    margin-bottom: 1rem;
  }
</style>
