import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CardList } from '../CardList'
import * as api from '../../api/preview'

vi.mock('../../api/preview')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('CardList', () => {
  const mockCards = [
    {
      id: 'card-1',
      type: 'cloze' as const,
      text: 'Test cloze card {{c1::answer}}',
      tags: ['tag1'],
      topics: [{ id: '1A', title: 'Structure and function of proteins' }],
      status: 'pending',
    },
    {
      id: 'card-2',
      type: 'vignette' as const,
      text: 'Test vignette card',
      tags: ['tag2'],
      topics: [{ id: '2A', title: 'Assemblies of molecules and cells' }],
      status: 'pending',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_renders_cards - List of CardPreview items', async () => {
    vi.mocked(api.fetchPreview).mockResolvedValue({
      cards: mockCards,
      total: 2,
      limit: 20,
      offset: 0,
    })

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('card-list')).toBeInTheDocument()
    })

    expect(screen.getAllByTestId('card-preview')).toHaveLength(2)
  })

  it('test_pagination - Page controls shown', async () => {
    vi.mocked(api.fetchPreview).mockResolvedValue({
      cards: mockCards,
      total: 50,
      limit: 20,
      offset: 0,
    })

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument()
    })

    expect(screen.getByTestId('page-info')).toHaveTextContent('1')
  })

  it('test_next_page - Loads next page', async () => {
    vi.mocked(api.fetchPreview).mockResolvedValue({
      cards: mockCards,
      total: 50,
      limit: 20,
      offset: 0,
    })

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument()
    })

    const nextButton = screen.getByTestId('next-page')
    fireEvent.click(nextButton)

    await waitFor(() => {
      expect(api.fetchPreview).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 20 })
      )
    })
  })

  it('test_filter_by_type - Type filter works', async () => {
    vi.mocked(api.fetchPreview).mockResolvedValue({
      cards: mockCards,
      total: 2,
      limit: 20,
      offset: 0,
    })

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('type-filter')).toBeInTheDocument()
    })

    const typeFilter = screen.getByTestId('type-filter')
    fireEvent.change(typeFilter, { target: { value: 'cloze' } })

    await waitFor(() => {
      expect(api.fetchPreview).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'cloze' })
      )
    })
  })

  it('test_empty_state - Message when no cards', async () => {
    vi.mocked(api.fetchPreview).mockResolvedValue({
      cards: [],
      total: 0,
      limit: 20,
      offset: 0,
    })

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    })

    expect(screen.getByText(/no cards/i)).toBeInTheDocument()
  })

  it('test_loading_state - Skeleton loading', () => {
    vi.mocked(api.fetchPreview).mockImplementation(
      () => new Promise(() => {})
    )

    render(<CardList jobId="job-123" />, { wrapper: createWrapper() })

    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument()
  })
})
