<script lang="ts">
  import type { Legal } from '../api'
  import { chipsFromBb, presets, toBb } from '../play'

  let {
    legal,
    pot,
    currentBet,
    disabled = false,
    onact,
  }: {
    legal: Legal
    pot: number
    currentBet: number
    disabled?: boolean
    onact: (kind: string, to?: number) => void
  } = $props()

  const options = $derived(
    legal.can_raise
      ? presets(pot, legal.to_call, currentBet, legal.min_raise_to, legal.max_raise_to)
      : [],
  )
  const raiseWord = $derived(legal.can_check ? 'Bet' : 'Raise')
  let custom = $state('')

  function sendCustom(event: SubmitEvent) {
    event.preventDefault()
    const to = chipsFromBb(Number(custom))
    if (Number.isFinite(to) && to >= legal.min_raise_to && to <= legal.max_raise_to) {
      onact(legal.can_check ? 'bet' : 'raise', to)
      custom = ''
    }
  }

  function onkeydown(event: KeyboardEvent) {
    if (disabled || event.metaKey || event.ctrlKey || event.altKey) return
    if (event.target instanceof HTMLInputElement) return
    const key = event.key.toLowerCase()
    if (key === 'f' && !legal.can_check) onact('fold')
    else if (key === 'c') onact(legal.can_check ? 'check' : 'call')
    else {
      const index = Number(key) - 1
      if (Number.isInteger(index) && index >= 0 && index < options.length) {
        onact(legal.can_check ? 'bet' : 'raise', options[index].to)
      }
    }
  }
</script>

<svelte:window {onkeydown} />

<div class="bar" role="group" aria-label="Your action">
  <div class="main">
    {#if !legal.can_check}
      <button type="button" class="fold" {disabled} onclick={() => onact('fold')}>Fold <kbd>F</kbd></button>
    {/if}
    {#if legal.can_check}
      <button type="button" {disabled} onclick={() => onact('check')}>Check <kbd>C</kbd></button>
    {:else}
      <button type="button" class="call" {disabled} onclick={() => onact('call')}
        >Call {toBb(legal.to_call)}bb <kbd>C</kbd></button
      >
    {/if}
  </div>
  {#if options.length}
    <div class="raises">
      {#each options as option, i (option.label)}
        <button
          type="button"
          class="raise"
          {disabled}
          onclick={() => onact(legal.can_check ? 'bet' : 'raise', option.to)}
        >
          {raiseWord}
          {option.label === 'All-in' ? 'all-in' : `${toBb(option.to)}bb`}
          <small>{option.label === 'All-in' ? `${toBb(option.to)}bb` : option.label}</small>
          <kbd>{i + 1}</kbd>
        </button>
      {/each}
      <form class="custom" onsubmit={sendCustom}>
        <input
          bind:value={custom}
          inputmode="decimal"
          aria-label="{raiseWord} to (bb)"
          placeholder="{toBb(legal.min_raise_to)}–{toBb(legal.max_raise_to)}bb"
          {disabled}
        />
        <button type="submit" {disabled}>{raiseWord}</button>
      </form>
    </div>
  {/if}
</div>

<style>
  .bar {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-top: 0.9rem;
  }
  .main,
  .raises {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  button {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 600;
  }
  .fold {
    border-color: var(--bad);
    color: var(--bad);
  }
  .call {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--on-accent);
  }
  .raise {
    flex-direction: column;
    gap: 0;
    min-width: 5.5rem;
  }
  .raise small {
    font-weight: 400;
    color: var(--muted);
  }
  kbd {
    font-size: 0.7rem;
    opacity: 0.7;
  }
  .custom {
    display: flex;
    gap: 0.4rem;
  }
  .custom input {
    width: 7.5rem;
    padding: 0.4rem 0.6rem;
  }
  @media (pointer: coarse) {
    kbd {
      display: none;
    }
  }
</style>
