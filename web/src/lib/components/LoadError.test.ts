import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import LoadError from './LoadError.svelte'

describe('LoadError', () => {
  it('says what failed and offers to try again', async () => {
    const onretry = vi.fn()
    render(LoadError, { message: 'Could not load stats: offline', onretry })
    expect(screen.getByRole('alert')).toHaveTextContent('Could not load stats: offline')
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onretry).toHaveBeenCalledTimes(1)
  })
})
