<script lang="ts">
  import { api, type DrillMeta } from '../api'
  import SpeedRound from '../components/SpeedRound.svelte'
  import { href } from '../router.svelte'

  let { selected = 'mixed' }: { selected?: string } = $props()

  let all = $state<DrillMeta[] | null>(null)
  let error = $state<string | null>(null)

  $effect(() => {
    api.drills().then(
      (list) => (all = list.filter((d) => d.speed)),
      (e: Error) => (error = e.message),
    )
  })

  const chosen = $derived(
    all === null ? [] : selected === 'mixed' ? all : all.filter((d) => d.key === selected),
  )
</script>

<nav class="crumbs"><a href={href('math-lab')}>← Math Lab</a></nav>
<h1>Speed round{chosen.length === 1 ? `: ${chosen[0].title}` : ''}</h1>

{#if error}
  <p role="alert">Could not load drills: {error}</p>
{:else if all === null}
  <p>Loading…</p>
{:else if chosen.length === 0}
  <p>“{selected}” has no speed round. Pick one below.</p>
{:else}
  <SpeedRound drills={chosen} roundKey={selected} />
{/if}

{#if all?.length}
  <h2>Other rounds</h2>
  <div class="others">
    <a href={href('speed', 'mixed')} aria-current={selected === 'mixed' ? 'page' : undefined}>Mixed</a>
    {#each all as drill (drill.key)}
      <a href={href('speed', drill.key)} aria-current={selected === drill.key ? 'page' : undefined}
        >{drill.title}</a
      >
    {/each}
  </div>
{/if}

<style>
  .crumbs {
    margin-bottom: 0.75rem;
  }
  .others {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .others a {
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: inherit;
    text-decoration: none;
  }
  .others a[aria-current='page'] {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
</style>
