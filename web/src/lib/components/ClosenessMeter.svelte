<script lang="ts">
  let {
    expected,
    response,
    tolerance,
  }: { expected: number; response: number; tolerance: number } = $props()

  const clamp = (v: number) => Math.min(100, Math.max(0, v))
  const close = $derived(Math.abs(response - expected) <= tolerance)
</script>

<div
  class="meter"
  role="img"
  aria-label="Your estimate {response}% against the answer {expected}%, accepted range ±{tolerance} points"
>
  <span class="track"></span>
  <span
    class="band"
    style:left="{clamp(expected - tolerance)}%"
    style:width="{clamp(expected + tolerance) - clamp(expected - tolerance)}%"
  ></span>
  <span class="mark answer" style:left="{clamp(expected)}%" title="Answer {expected}%"></span>
  <span class="mark you" class:close style:left="{clamp(response)}%" title="You {response}%"></span>
  <span class="tick" style:left="0%">0</span>
  <span class="tick" style:left="50%">50</span>
  <span class="tick" style:left="100%">100</span>
</div>

<style>
  .meter {
    position: relative;
    height: 2.2rem;
    margin: 0.4rem 0.5rem 0.6rem;
  }
  .track {
    position: absolute;
    left: 0;
    right: 0;
    top: 0.42rem;
    height: 10px;
    border-radius: 999px;
    border: 2px solid var(--ink);
    background: var(--surface);
  }
  .band {
    position: absolute;
    top: 0.55rem;
    height: 6px;
    border-radius: 3px;
    background: var(--mint);
  }
  .mark {
    position: absolute;
    top: 0.2rem;
    width: 4px;
    height: 0.95rem;
    margin-left: -2px;
    border-radius: 2px;
  }
  .answer {
    background: var(--good);
  }
  .you {
    background: var(--bad);
    width: 1rem;
    height: 1rem;
    top: 0.2rem;
    margin-left: -0.5rem;
    border-radius: 50%;
    border: 2px solid var(--ink);
    transition: left 0.5s cubic-bezier(0.3, 1.3, 0.5, 1);
  }
  .you.close {
    background: var(--good);
  }
  .tick {
    position: absolute;
    top: 1.15rem;
    transform: translateX(-50%);
    font-size: 0.7rem;
    color: var(--muted);
  }
</style>
