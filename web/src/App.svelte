<script lang="ts">
  import Home from './lib/pages/Home.svelte'
  import Learn from './lib/pages/Learn.svelte'
  import MathLab from './lib/pages/MathLab.svelte'
  import Play from './lib/pages/Play.svelte'
  import Preflop from './lib/pages/Preflop.svelte'
  import Review from './lib/pages/Review.svelte'
  import Speed from './lib/pages/Speed.svelte'
  import Stats from './lib/pages/Stats.svelte'
  import Today from './lib/pages/Today.svelte'
  import { href, router } from './lib/router.svelte'

  const NAV = [
    { page: 'today', label: 'Today' },
    { page: 'learn', label: 'Learn' },
    { page: 'math-lab', label: 'Math Lab' },
    { page: 'preflop', label: 'Preflop' },
    { page: 'play', label: 'Play' },
    { page: 'stats', label: 'Progress' },
  ]
  const route = $derived(router.route)
  const TITLES: Record<string, string> = {
    home: 'Home',
    today: 'Today',
    learn: 'Learn',
    'math-lab': 'Math Lab',
    preflop: 'Preflop',
    speed: 'Speed round',
    play: 'Play',
    review: 'Review',
    stats: 'Progress',
  }
  $effect(() => {
    document.title = `${TITLES[route.page] ?? 'Not found'} · Hold'em Trainer`
  })
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
  {:else if route.page === 'today'}
    <Today />
  {:else if route.page === 'learn'}
    {#key route.params[0]}
      <Learn selected={route.params[0]} />
    {/key}
  {:else if route.page === 'math-lab'}
    {#key route.params[0]}
      <MathLab selected={route.params[0]} />
    {/key}
  {:else if route.page === 'preflop'}
    {#key route.params.join('/')}
      <Preflop params={route.params} />
    {/key}
  {:else if route.page === 'play'}
    <Play />
  {:else if route.page === 'review'}
    {#key route.params[0]}
      <Review selected={route.params[0]} />
    {/key}
  {:else if route.page === 'speed'}
    {#key route.params[0]}
      <Speed selected={route.params[0]} />
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
    max-width: 100%;
    overflow-x: auto;
    padding: 4px; /* room for the focus ring inside the scroll area */
  }
  nav a {
    white-space: nowrap;
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
  @media (max-width: 520px) {
    nav a {
      padding: 0.4rem 0.5rem;
    }
  }
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
  }
</style>
