<script lang="ts">
  /** A failed load with a way out: say what went wrong and offer to try again. */
  let { message, onretry }: { message: string; onretry: () => void } = $props()
</script>

<div class="retry" role="alert">
  <p>{message}</p>
  <button type="button" onclick={onretry}>Try again</button>
</div>
