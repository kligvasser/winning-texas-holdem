<script lang="ts">
  import { api, type Curriculum, type DrillMeta } from '../api'
  import LoadError from '../components/LoadError.svelte'
  import { groupByTier, percent, TIER_NAMES } from '../format'
  import { href } from '../router.svelte'

  let { selected = undefined }: { selected?: string } = $props()

  let curriculum = $state<Curriculum | null>(null)
  let drills = $state<DrillMeta[]>([])
  let error = $state<string | null>(null)

  function load() {
    error = null
    Promise.all([api.curriculum(), api.drills()]).then(
      ([c, d]: [Curriculum, DrillMeta[]]) => {
        curriculum = c
        drills = d
      },
      (e: Error) => (error = e.message),
    )
  }

  $effect(load)

  const byId = $derived(new Map(curriculum?.concepts.map((c) => [c.id, c])))
  const concept = $derived(selected ? byId.get(selected) : undefined)
  const drillTitle = (key: string) => drills.find((d) => d.key === key)?.title ?? key
</script>

{#if error}
  <LoadError message="Could not load the curriculum: {error}" onretry={load} />
{:else if curriculum === null}
  <p>Loading…</p>
{:else if selected && !concept}
  <p>Unknown concept “{selected}”. <a href={href('learn')}>All concepts</a></p>
{:else if concept}
  <nav class="crumbs"><a href={href('learn')}>← Curriculum</a></nav>
  <p class="eyebrow">Tier {concept.tier} · {TIER_NAMES[concept.tier]}</p>
  <h1>{concept.title}</h1>
  <p class="lead">{concept.summary}</p>
  {#if concept.attempts}
    <p class="mastery">
      <span class="badge-inline status-{concept.status}">{concept.status}</span>
      Mastery {percent(concept.mastery)} over your last {concept.attempts} answers
      <span class="bar" aria-hidden="true"><span style:width={percent(concept.mastery)}></span></span>
    </p>
  {/if}
  <ul class="points">
    {#each concept.points as point, i (i)}<li>{point}</li>{/each}
  </ul>

  {#if concept.drills.length}
    <h2>Drill it</h2>
    <div class="actions">
      {#each concept.drills as key (key)}
        <a class="button" href={href('math-lab', key)}>{drillTitle(key)}</a>
      {/each}
    </div>
  {:else}
    <p class="muted">Coming soon: drills for this concept are on the roadmap.</p>
  {/if}

  {#if concept.prerequisites.length}
    <h2>Builds on</h2>
    <p>
      {#each concept.prerequisites as id, i (id)}{i ? ', ' : ''}<a href={href('learn', id)}
          >{byId.get(id)?.title ?? id}</a
        >{/each}
    </p>
  {/if}

  <h2>Watch and read</h2>
  <ul>
    {#each concept.lectures as lecture (lecture.label)}
      <li><a href={lecture.url} target="_blank" rel="noreferrer">{lecture.label}</a></li>
    {/each}
  </ul>
{:else}
  <h1>Curriculum</h1>
  <p class="lead">
    Concepts from MIT 15.S50, in the order they build on each other. Mastery is your smoothed
    accuracy over the last 20 answers.
  </p>
  {#each groupByTier(curriculum.concepts) as [tier, concepts] (tier)}
    <h2>Tier {tier} · {TIER_NAMES[tier]}</h2>
    <div class="grid">
      {#each concepts as c (c.id)}
        <a class="tile status-{c.status}" href={href('learn', c.id)}>
          <span class="row">
            <strong>{c.title}</strong>
            <span class="badge">{c.status}</span>
          </span>
          <span class="summary">{c.summary}</span>
          {#if c.attempts}
            <span class="bar" aria-label="Mastery {percent(c.mastery)}">
              <span style:width={percent(c.mastery)}></span>
            </span>
          {/if}
        </a>
      {/each}
    </div>
  {/each}
  <h2>Course materials</h2>
  <ul>
    {#each curriculum.materials as m (m.label)}
      <li><a href={m.url} target="_blank" rel="noreferrer">{m.label}</a></li>
    {/each}
  </ul>
{/if}

<style>
  .lead,
  .muted,
  .summary {
    color: var(--muted);
  }
  .mastery {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.9rem;
  }
  .mastery .bar {
    width: 8rem;
  }
  .badge-inline {
    font-size: 0.72rem;
    text-transform: uppercase;
    padding: 0.1rem 0.45rem;
    font-weight: 800;
    border-radius: 999px;
    border: var(--line);
    background: var(--sun);
    color: var(--on-bright);
  }
  .eyebrow {
    margin: 0;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
  }
  .points {
    line-height: 1.6;
    padding: 1rem 1.2rem 1rem 2.2rem;
    border-radius: 1.1rem;
    background: var(--surface);
    border: var(--line);
    box-shadow: var(--drop);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .button {
    padding: 0.55rem 1rem;
    border-radius: 0.9rem;
    background: linear-gradient(var(--mint), #3fc66b);
    color: var(--on-bright);
    text-decoration: none;
    border: var(--line);
    box-shadow: var(--drop-sm);
    font-weight: 800;
  }
  .button:active {
    transform: translateY(3px);
    box-shadow: none;
  }
  .crumbs {
    margin-bottom: 0.75rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
    gap: 1rem;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
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
  .tile.status-learning {
    background: color-mix(in srgb, var(--sun) var(--wash), var(--surface));
  }
  .tile.status-mastered {
    background: color-mix(in srgb, var(--mint) var(--wash), var(--surface));
  }
  .row {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    align-items: baseline;
  }
  .summary {
    font-size: 0.9rem;
  }
  .badge {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.1rem 0.45rem;
    font-weight: 800;
    border-radius: 999px;
    border: var(--line);
    background: var(--surface);
    color: var(--muted);
  }
  .status-learning .badge {
    background: var(--sun);
    color: var(--on-bright);
  }
  .status-mastered .badge {
    background: var(--mint);
    color: var(--on-bright);
  }
  .bar {
    height: 10px;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: var(--surface);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    background: var(--accent);
  }
</style>
