/** Keyboard helpers shared by the pages. */

/**
 * Stop a held Enter or Space from pressing a focused button again and again.
 * Without it, holding Enter on "Next" answers the following question too.
 */
export function ignoreHeld(event: KeyboardEvent): void {
  if (event.repeat && (event.key === 'Enter' || event.key === ' ')) event.preventDefault()
}
