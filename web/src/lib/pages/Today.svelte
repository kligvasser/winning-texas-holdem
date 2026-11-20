<script lang="ts">
  import { api, type DailyPlan, type DrillMeta } from '../api'
  import DrillRunner from '../components/DrillRunner.svelte'
  import { untrack } from 'svelte'
  import LoadError from '../components/LoadError.svelte'
  import { href } from '../router.svelte'
  import { loadSession, saveSession, type SavedSession, type SessionProgress } from '../session'

  let { day = new Date().toLocaleDateString('en-CA') }: { day?: string } = $props()

  let plan = $state<DailyPlan | null>(null)
  let drills = $state<DrillMeta[]>([])
  let error = $state<string | null>(null)
  let saved = $state<SavedSession | null>(untrack(() => loadSession(day)))
  let active = $state<SavedSession | null>(null)

  function start(session: SavedSession) {
    active = session
  }

  function progress(queue: string[], p: SessionProgress) {
    // Keep the session until it is finished, so a reload can resume it.
    saveSession(p.position >= queue.length ? null : { day, queue, progress: p })
  }

  function startOver() {
    saveSession(null)
    saved = null
  }

  function load() {
    error = null
    Promise.all([api.today(), api.drills()]).then(
      ([p, d]: [DailyPlan, DrillMeta[]]) => {
        plan = p
        drills = d
      },
      (e: Error) => (error = e.message),
    )
  }

  $effect(load)

  const title = (key: string) => drills.find((d) => d.key === key)?.title ?? key
</script>

<h1>Today</h1>

{#if error}
  <LoadError message="Could not load today's session: {error}" onretry={load} />
{:else if plan === null}
  <p>Loading…</p>
{:else if active}
  {@const queue = active.queue}
  <DrillRunner
    {drills}
    {queue}
    resume={active.progress}
    onprogress={(p) => progress(queue, p)}
  />
{:else if saved}
  <p class="lead">
    You have a session in progress: question {saved.progress.position + 1} of {saved.queue.length}.
  </p>
  <div class="actions">
    <button type="button" class="start" onclick={() => start(saved!)}>Resume session</button>
    <button type="button" onclick={startOver}>Start over</button>
  </div>
{:else if plan.queue.length === 0}
  <p>
    Nothing is due. Explore the <a href={href('learn')}>curriculum</a> or practise freely in the
    <a href={href('math-lab')}>Math Lab</a>.
  </p>
{:else}
  <p class="lead">
    {plan.queue.length} questions, a few from each drill, mixed together. The app spaces each drill
    out: ones you know well come back after days, ones you miss come back soon.
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
  <button
    type="button"
    class="start"
    onclick={() =>
      start({ day, queue: plan!.queue, progress: { position: 0, results: [], skipped: 0 } })}
    >Start session</button
  >
{/if}

<style>
  .lead {
    color: var(--muted);
  }
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
    margin: 1rem 0;
  }
  section {
    padding: 0.75rem 1rem;
    border-radius: 1.1rem;
    background: color-mix(in srgb, var(--tint) var(--wash), var(--surface));
    border: var(--line);
    box-shadow: var(--drop);
  }
  section:nth-child(3n + 1) { --tint: var(--tomato); }
  section:nth-child(3n + 2) { --tint: var(--mint); }
  section:nth-child(3n) { --tint: var(--skyblue); }
  h2 {
    margin: 0 0 0.4rem;
    font-size: 0.95rem;
  }
  ul {
    margin: 0;
    padding-left: 1.1rem;
  }
  .actions {
    display: flex;
    gap: 0.5rem;
  }
  .start {
    padding: 0.7rem 1.6rem;
    border-width: 3px;
    background: linear-gradient(#ffe94d, var(--sun-deep));
    color: var(--on-bright);
    font-size: 1.1rem;
    font-weight: 900;
  }
</style>
