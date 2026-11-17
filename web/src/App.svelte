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
  import Toy from './lib/pages/Toy.svelte'
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
    toy: 'Toy games',
    play: 'Play',
    review: 'Review',
    stats: 'Progress',
  }
  $effect(() => {
    document.title = `${TITLES[route.page] ?? 'Not found'} · Hold'em Trainer`
  })
</script>

<header class="topbar">
  <a class="brand" href={href('home')}><span class="logo">♠</span> Hold'em Trainer</a>
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
  {:else if route.page === 'toy'}
    <Toy />
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
    padding: 0.6rem 1rem;
    border-bottom: 3px solid var(--ink);
    background: var(--bar);
  }
  .logo {
    display: inline-grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    border: 3px dashed #fff;
    outline: 2px solid var(--ink);
    background: #e5484d;
    color: #fff;
    box-shadow: 0 3px 0 var(--ink);
    transition: transform 0.4s cubic-bezier(0.3, 1.6, 0.5, 1);
  }
  .brand:hover .logo {
    transform: rotate(180deg);
  }
  .brand {
    font-weight: 900;
    font-size: 1.2rem;
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
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    border: 2px solid transparent;
    color: var(--text);
    font-weight: 800;
    text-decoration: none;
  }
  nav a:hover {
    background: color-mix(in srgb, var(--surface) 55%, transparent);
  }
  nav a[aria-current='page'] {
    background: var(--surface);
    border-color: var(--ink);
    color: var(--text);
    box-shadow: 0 2px 0 var(--ink);
  }
  @media (max-width: 520px) {
    nav a {
      padding: 0.4rem 0.5rem;
    }
  }
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 1.5rem 1rem 8rem;
  }
</style>
