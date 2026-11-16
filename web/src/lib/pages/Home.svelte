<script lang="ts">
  import PlayingCard from '../components/PlayingCard.svelte'
  import { href } from '../router.svelte'
</script>

<section class="hero">
  <div class="fan" aria-hidden="true">
    <PlayingCard code="As" />
    <PlayingCard code="Kh" />
  </div>
  <div>
    <h1>Winning Texas Hold'em</h1>
    <p>
      Practice the maths until it is automatic, then the decisions. Built around MIT 15.S50, with
      every answer computed and explained, and reviews scheduled for when you are about to forget.
    </p>
    <a class="cta" href={href('today')}>Today's session</a>
  </div>
</section>

<div class="grid">
  <a class="tile" href={href('learn')}>
    <strong>Learn</strong>
    <span>The curriculum, concept by concept, with lecture links and your mastery.</span>
  </a>
  <a class="tile" href={href('math-lab')}>
    <strong>Math Lab</strong>
    <span>Outs, pot odds, equity, combos, flop odds, MDF and more.</span>
  </a>
  <a class="tile" href={href('preflop')}>
    <strong>Preflop</strong>
    <span>Opening and defending charts, paint-the-range, and your weakest spots.</span>
  </a>
  <a class="tile" href={href('stats')}>
    <strong>Progress</strong>
    <span>Accuracy, speed and estimation bias for each drill.</span>
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
    margin-bottom: 1.5rem;
  }
  .hero p {
    max-width: 34rem;
    opacity: 0.9;
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
    padding: 0.65rem 1.2rem;
    border-radius: 0.6rem;
    background: var(--accent);
    color: var(--on-accent);
    font-weight: 600;
    text-decoration: none;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
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
