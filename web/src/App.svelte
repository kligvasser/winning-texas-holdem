<script lang="ts">
  import Home from './lib/pages/Home.svelte'
  import MathLab from './lib/pages/MathLab.svelte'
  import Stats from './lib/pages/Stats.svelte'
  import { href, router } from './lib/router.svelte'

  const NAV = [
    { page: 'home', label: 'Home' },
    { page: 'math-lab', label: 'Math Lab' },
    { page: 'stats', label: 'Progress' },
  ]
  const route = $derived(router.route)
</script>

<header class="topbar">
  <a class="brand" href={href('home')}>♠ Hold'em Trainer</a>
  <nav>
    {#each NAV as item (item.page)}
      <a href={href(item.page)} aria-current={route.page === item.page ? 'page' : undefined}>
        {item.label}
      </a>
    {/each}
  </nav>
</header>

<main>
  {#if route.page === 'home'}
    <Home />
  {:else if route.page === 'math-lab'}
    {#key route.params[0]}
      <MathLab selected={route.params[0]} />
    {/key}
  {:else if route.page === 'stats'}
    <Stats />
  {:else}
    <h1>Not found</h1>
    <p><a href={href('home')}>Back to the start</a></p>
  {/if}
</main>

<style>
  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .brand {
    font-weight: 800;
    color: inherit;
    text-decoration: none;
  }
  nav {
    display: flex;
    gap: 0.25rem;
  }
  nav a {
    padding: 0.4rem 0.75rem;
    border-radius: 0.5rem;
    color: var(--muted);
    text-decoration: none;
  }
  nav a[aria-current='page'] {
    background: var(--accent-soft);
    color: var(--text);
    font-weight: 600;
  }
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
  }
</style>
