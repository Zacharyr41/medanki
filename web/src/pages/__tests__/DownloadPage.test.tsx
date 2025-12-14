import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DownloadPage } from '../DownloadPage'
import * as api from '../../api/preview'
import * as downloadApi from '../../api/download'

vi.mock('../../api/preview')
vi.mock('../../api/download')

const createWrapper = (jobId: string = 'job-123') => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/download/${jobId}`]}>
        <Routes>
          <Route path="/download/:jobId" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DownloadPage', () => {
  const mockStats = {
    counts: { total: 50, cloze: 30, vignette: 15, basic_qa: 5 },
    topics: { cardiology: 20, neurology: 30 },
    timing: {
      created_at: '2024-01-15T10:00:00Z',
      completed_at: '2024-01-15T10:02:00Z',
      duration_seconds: 120,
    },
  }

  const mockPreview = {
    cards: [
      {
        id: 'card-1',
        type: 'cloze' as const,
        text: 'Test card',
        tags: ['tag1'],
        topics: ['1A'],
        status: 'pending',
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchStats).mockResolvedValue(mockStats)
    vi.mocked(api.fetchPreview).mockResolvedValue(mockPreview)
  })

  it('test_shows_statistics - Statistics component', async () => {
    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('statistics')).toBeInTheDocument()
    })
  })

  it('test_shows_card_preview - CardList component', async () => {
    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('card-list')).toBeInTheDocument()
    })
  })

  it('test_download_button - Download button present', async () => {
    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('download-button')).toBeInTheDocument()
    })
  })

  it('test_download_triggers_file - Blob download works', async () => {
    const mockBlob = new Blob(['test'], { type: 'application/octet-stream' })
    vi.mocked(downloadApi.downloadDeck).mockResolvedValue(mockBlob)

    const createObjectURL = vi.fn(() => 'blob:test-url')
    const revokeObjectURL = vi.fn()
    global.URL.createObjectURL = createObjectURL
    global.URL.revokeObjectURL = revokeObjectURL

    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('download-button')).toBeInTheDocument()
    })

    const downloadButton = screen.getByTestId('download-button')
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(downloadApi.downloadDeck).toHaveBeenCalledWith('job-123')
    })
  })

  it('test_new_upload_link - Link back to upload', async () => {
    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('upload-link')).toBeInTheDocument()
    })

    expect(screen.getByTestId('upload-link')).toHaveAttribute('href', '/')
  })

  it('test_regenerate_button - Regenerate option', async () => {
    vi.mocked(downloadApi.regenerateDeck).mockResolvedValue({ job_id: 'new-job' })

    render(<DownloadPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('regenerate-button')).toBeInTheDocument()
    })

    const regenerateButton = screen.getByTestId('regenerate-button')
    fireEvent.click(regenerateButton)

    await waitFor(() => {
      expect(downloadApi.regenerateDeck).toHaveBeenCalledWith('job-123')
    })
  })
})
