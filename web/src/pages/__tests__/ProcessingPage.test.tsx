import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProcessingPage } from '../ProcessingPage'
import type { Status, Stage } from '../../hooks/useWebSocket'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const mockWebSocketState: {
  progress: number
  stage: Stage
  status: Status
  error: string | null
  fileName: string
} = {
  progress: 0,
  stage: 'ingesting',
  status: 'connected',
  error: null,
  fileName: 'test.pdf',
}

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => mockWebSocketState,
}))

function renderWithRouter(jobId: string) {
  return render(
    <MemoryRouter initialEntries={[`/processing/${jobId}`]}>
      <Routes>
        <Route path="/processing/:id" element={<ProcessingPage />} />
        <Route path="/download/:id" element={<div>Download Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProcessingPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    mockWebSocketState.progress = 0
    mockWebSocketState.stage = 'ingesting'
    mockWebSocketState.status = 'connected'
    mockWebSocketState.error = null
    mockWebSocketState.fileName = 'test.pdf'
  })

  it('shows progress bar', () => {
    mockWebSocketState.progress = 50
    renderWithRouter('job-123')

    expect(screen.getByTestId('progress-bar')).toBeInTheDocument()
  })

  it('shows stage list', () => {
    renderWithRouter('job-123')

    expect(screen.getByTestId('stage-list')).toBeInTheDocument()
  })

  it('shows file info', () => {
    mockWebSocketState.fileName = 'medical_notes.pdf'
    renderWithRouter('job-123')

    expect(screen.getByText(/medical_notes\.pdf/)).toBeInTheDocument()
  })

  it('has cancel button', () => {
    renderWithRouter('job-123')

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('navigates on complete', async () => {
    mockWebSocketState.status = 'complete'
    mockWebSocketState.progress = 100
    renderWithRouter('job-123')

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/download/job-123')
    })
  })

  it('shows error state', () => {
    mockWebSocketState.status = 'error'
    mockWebSocketState.error = 'Something went wrong'
    renderWithRouter('job-123')

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })
})
