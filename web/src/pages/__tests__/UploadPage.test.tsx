import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import { UploadPage } from '../UploadPage'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: vi.fn(),
  }
})

vi.mock('../../api/upload', () => ({
  uploadFile: vi.fn(),
}))

import { uploadFile } from '../../api/upload'

const renderWithRouter = (component: React.ReactNode) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('UploadPage', () => {
  const mockNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useNavigate).mockReturnValue(mockNavigate)
  })

  it('renders file upload component', () => {
    renderWithRouter(<UploadPage />)
    expect(screen.getByTestId('dropzone')).toBeInTheDocument()
  })

  it('renders options panel', () => {
    renderWithRouter(<UploadPage />)
    expect(screen.getByLabelText(/exam/i)).toBeInTheDocument()
  })

  it('has submit button disabled without file', () => {
    renderWithRouter(<UploadPage />)
    const button = screen.getByRole('button', { name: /generate/i })
    expect(button).toBeDisabled()
  })

  it('has submit button enabled with file', async () => {
    renderWithRouter(<UploadPage />)

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    const button = screen.getByRole('button', { name: /generate/i })
    expect(button).toBeEnabled()
  })

  it('navigates on successful submit', async () => {
    vi.mocked(uploadFile).mockResolvedValue({ jobId: 'job-123' })
    renderWithRouter(<UploadPage />)

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    const button = screen.getByRole('button', { name: /generate/i })
    await userEvent.click(button)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/processing/job-123')
    })
  })

  it('shows error on failure', async () => {
    vi.mocked(uploadFile).mockRejectedValue(new Error('Upload failed'))
    renderWithRouter(<UploadPage />)

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    const button = screen.getByRole('button', { name: /generate/i })
    await userEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
    })
  })
})
