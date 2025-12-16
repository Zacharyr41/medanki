import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SaveCardsButton } from '../SaveCardsButton'
import { useAuthStore } from '../../stores/authStore'

vi.mock('../../api/savedCards', () => ({
  saveCards: vi.fn().mockResolvedValue({ saved_count: 2, message: 'Saved 2 cards' }),
}))

describe('SaveCardsButton', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    vi.clearAllMocks()
  })

  it('is disabled when no selection', () => {
    render(
      <SaveCardsButton jobId="job123" selectedCardIds={[]} onSaved={() => {}} />
    )

    const button = screen.getByTestId('save-cards-button')
    expect(button).toBeDisabled()
  })

  it('shows login prompt when unauthenticated', () => {
    render(
      <SaveCardsButton
        jobId="job123"
        selectedCardIds={['card1', 'card2']}
        onSaved={() => {}}
      />
    )

    const button = screen.getByTestId('save-cards-button')
    fireEvent.click(button)

    expect(screen.getByTestId('login-prompt')).toBeInTheDocument()
  })

  it('saves cards when authenticated', async () => {
    const { saveCards } = await import('../../api/savedCards')
    const onSaved = vi.fn()

    useAuthStore.getState().login(
      {
        id: 'user123',
        email: 'test@gmail.com',
        name: 'Test User',
        picture_url: null,
      },
      'mock-token'
    )

    render(
      <SaveCardsButton
        jobId="job123"
        selectedCardIds={['card1', 'card2']}
        onSaved={onSaved}
      />
    )

    const button = screen.getByTestId('save-cards-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(saveCards).toHaveBeenCalledWith({
        job_id: 'job123',
        card_ids: ['card1', 'card2'],
      })
    })

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled()
    })
  })

  it('shows selection count in button text', () => {
    useAuthStore.getState().login(
      {
        id: 'user123',
        email: 'test@gmail.com',
        name: 'Test User',
        picture_url: null,
      },
      'mock-token'
    )

    render(
      <SaveCardsButton
        jobId="job123"
        selectedCardIds={['card1', 'card2', 'card3']}
        onSaved={() => {}}
      />
    )

    expect(screen.getByText(/Save 3 Cards/i)).toBeInTheDocument()
  })

  it('shows success message after saving', async () => {
    useAuthStore.getState().login(
      {
        id: 'user123',
        email: 'test@gmail.com',
        name: 'Test User',
        picture_url: null,
      },
      'mock-token'
    )

    render(
      <SaveCardsButton
        jobId="job123"
        selectedCardIds={['card1', 'card2']}
        onSaved={() => {}}
      />
    )

    const button = screen.getByTestId('save-cards-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText(/Saved 2 cards/i)).toBeInTheDocument()
    })
  })
})
