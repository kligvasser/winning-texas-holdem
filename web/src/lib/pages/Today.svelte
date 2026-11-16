<script lang="ts">
  import { api, type DailyPlan, type DrillMeta } from '../api'
  import DrillRunner from '../components/DrillRunner.svelte'
  import { href } from '../router.svelte'

  let plan = $state<DailyPlan | null>(null)
  let drills = $state<DrillMeta[]>([])
  let error = $state<string | null>(null)
  let started = $state(false)

  $effect(() => {
    Promise.all([api.today(), api.drills()]).then(
      ([p, d]: [DailyPlan, DrillMeta[]]) => {
        plan = p
        drills = d
      },
      (e: Error) => (error = e.message),
    )
  })

  const title = (key: string) => drills.find((d) => d.key === key)?.title ?? key
</script>

<h1>Today</h1>

{#if error}
  <p role="alert">Could not load today's session: {error}</p>
{:else if plan === null}
  <p>Loading…</p>
{:else if started}
  <DrillRunner {drills} queue={plan.queue} />
{:else if plan.queue.length === 0}
  <p>
    Nothing is due. Explore the <a href={href('learn')}>curriculum</a> or practise freely in the
    <a href={href('math-lab')}>Math Lab</a>.
  </p>
{:else}
  <p class="lead">
    {plan.queue.length} questions, interleaved across drills. Each drill's answers are scored together
    and scheduled for review.
  </p>
  <div class="groups">
    {#each [{ label: 'Due for review', keys: plan.due }, { label: 'New today', keys: plan.new }, { label: 'Extra practice: lowest recall', keys: plan.extra }] as group (group.label)}
      {#if group.keys.length}
        <section>
          <h2>{group.label}</h2>
          <ul>
            {#each group.keys as key (key)}<li>{title(key)}</li>{/each}
          </ul>
        </section>
      {/if}
    {/each}
  </div>
  <button type="button" class="start" onclick={() => (started = true)}>Start session</button>
{/if}

<style>
  .lead {
    color: var(--muted);
  }
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 0.75rem;
    margin: 1rem 0;
  }
  section {
    padding: 0.75rem 1rem;
    border-radius: 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  h2 {
    margin: 0 0 0.4rem;
    font-size: 0.95rem;
  }
  ul {
    margin: 0;
    padding-left: 1.1rem;
  }
  .start {
    background: var(--accent);
    color: var(--on-accent);
    border-color: var(--accent);
    font-weight: 600;
  }
</style>
