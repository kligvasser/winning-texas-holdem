<script lang="ts">
  import { api, type Activity, type DailyPlan } from '../api'
  import GoalRing from '../components/GoalRing.svelte'
  import PlayingCard from '../components/PlayingCard.svelte'
  import { DAILY_GOAL } from '../format'
  import { href } from '../router.svelte'

  let dashboard = $state<{ activity: Activity; plan: DailyPlan } | null>(null)

  $effect(() => {
    // The dashboard is a bonus: if it fails to load, the page still works without it.
    Promise.all([api.activity(), api.today()]).then(
      ([activity, plan]: [Activity, DailyPlan]) => (dashboard = { activity, plan }),
      () => {},
    )
  })

  const activity = $derived(dashboard?.activity)
  const queued = $derived(dashboard?.plan.queue.length ?? 0)

  const greeting = $derived.by(() => {
    if (!activity || activity.total === 0) return 'Welcome! Start with a short session.'
    if (activity.answered_today >= DAILY_GOAL) return 'Daily goal done. Nice work.'
    if (activity.practiced_today) return 'Good to see you back. Keep the streak going.'
    if (activity.streak) return `Your ${activity.streak}-day streak is waiting for today's session.`
    return 'Welcome back. A short session gets you rolling again.'
  })
</script>

<section class="hero">
  <div class="fan" aria-hidden="true">
    <PlayingCard code="As" />
    <PlayingCard code="Kh" order={1} />
  </div>
  <div>
    <h1>Winning Texas Hold'em</h1>
    <p>{greeting}</p>
    <a class="cta" href={href('today')}>
      {queued ? `Start today's session · ${queued} questions` : "Today's session"}
    </a>
  </div>
</section>

{#if dashboard}
  {@const { activity, plan } = dashboard}
  <section class="dashboard" aria-label="Your practice">
    <div class="stat">
      <GoalRing value={activity.answered_today} goal={DAILY_GOAL} label="Answers today" />
      <span>Today's goal</span>
    </div>
    <div class="stat">
      <strong class="flame" class:cold={!activity.practiced_today}>🔥 {activity.streak}</strong>
      <span>day streak · best {activity.best_streak}</span>
    </div>
    <div class="stat">
      <strong>{plan.due.length}</strong>
      <span>drills due for review</span>
    </div>
    <div class="stat">
      <strong>{activity.total}</strong>
      <span>answers all time</span>
    </div>
  </section>
{/if}

<div class="grid">
  <a class="tile" href={href('learn')}>
    <strong>📚 Learn</strong>
    <span>The curriculum, concept by concept, with lecture links and your mastery.</span>
  </a>
  <a class="tile" href={href('math-lab')}>
    <strong>🧮 Math Lab</strong>
    <span>Outs, pot odds, equity, combos, flop odds, MDF and more.</span>
  </a>
  <a class="tile" href={href('speed', 'mixed')}>
    <strong>⚡ Speed round</strong>
    <span>60 seconds, as many quick answers as you can. Beat your best.</span>
  </a>
  <a class="tile" href={href('preflop')}>
    <strong>🃏 Preflop</strong>
    <span>Opening and defending charts, paint-the-range, and your weakest spots.</span>
  </a>
  <a class="tile" href={href('stats')}>
    <strong>📈 Progress</strong>
    <span>Activity, accuracy, speed and estimation bias for each drill.</span>
  </a>
</div>

<style>
  .hero {
    display: flex;
    gap: 2rem;
    align-items: center;
    padding: 2rem;
    border-radius: 1.25rem;
    background: radial-gradient(ellipse at 30% 40%, var(--felt-light), var(--felt));
    color: var(--felt-text);
    margin-bottom: 1rem;
  }
  .hero p {
    max-width: 34rem;
    opacity: 0.92;
  }
  .fan {
    display: flex;
    --card-w: 4.5rem;
  }
  .fan :global(.card:last-child) {
    transform: rotate(10deg) translate(-1.2rem, 0.3rem);
  }
  .fan :global(.card:first-child) {
    transform: rotate(-8deg);
  }
  .cta {
    display: inline-block;
    padding: 0.7rem 1.3rem;
    border-radius: 0.6rem;
    background: #f2b544;
    color: #1d1505;
    font-weight: 700;
    text-decoration: none;
    box-shadow: 0 4px 14px rgb(0 0 0 / 0.25);
    transition: transform 0.12s ease;
  }
  .cta:hover {
    transform: translateY(-2px);
  }
  .dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 1rem;
    border-radius: 0.9rem;
    background: var(--surface);
    border: 1px solid var(--border);
    text-align: center;
  }
  .stat strong {
    font-size: 1.9rem;
    font-variant-numeric: tabular-nums;
  }
  .stat span {
    color: var(--muted);
    font-size: 0.85rem;
  }
  .flame.cold {
    filter: grayscale(1);
    opacity: 0.7;
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
    padding: 1rem 1.1rem;
    border-radius: 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
    transition:
      transform 0.12s ease,
      border-color 0.15s;
  }
  .tile:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
  }
  .tile span {
    color: var(--muted);
    font-size: 0.92rem;
  }
  @media (max-width: 600px) {
    .hero {
      flex-direction: column;
      text-align: center;
      padding: 1.5rem 1rem;
    }
  }
</style>
