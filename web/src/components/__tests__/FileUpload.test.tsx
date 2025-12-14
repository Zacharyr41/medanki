import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { FileUpload } from '../FileUpload'

describe('FileUpload', () => {
  it('renders dropzone', () => {
    render(<FileUpload onFileSelect={vi.fn()} />)
    expect(screen.getByText(/drop.*file/i)).toBeInTheDocument()
  })

  it('accepts pdf files', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    expect(onFileSelect).toHaveBeenCalledWith(file)
  })

  it('accepts md files', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['# Test'], 'test.md', { type: 'text/markdown' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    expect(onFileSelect).toHaveBeenCalledWith(file)
  })

  it('rejects unsupported files via drag and drop', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['test'], 'test.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const dropzone = screen.getByTestId('dropzone')

    fireEvent.drop(dropzone, {
      dataTransfer: { files: [file] },
    })

    expect(onFileSelect).not.toHaveBeenCalled()
    expect(screen.getByText(/unsupported.*file/i)).toBeInTheDocument()
  })

  it('shows file preview', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['test content'], 'study-notes.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    expect(screen.getByText('study-notes.pdf')).toBeInTheDocument()
  })

  it('has remove file button', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    const removeButton = screen.getByRole('button', { name: /remove/i })
    await userEvent.click(removeButton)

    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
    expect(onFileSelect).toHaveBeenLastCalledWith(null)
  })

  it('highlights on drag enter', () => {
    render(<FileUpload onFileSelect={vi.fn()} />)

    const dropzone = screen.getByTestId('dropzone')
    fireEvent.dragEnter(dropzone)

    expect(dropzone).toHaveClass('drag-active')
  })

  it('calls onFileSelect callback', async () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const file = new File(['test'], 'notes.pdf', { type: 'application/pdf' })
    const input = screen.getByTestId('file-input')
    await userEvent.upload(input, file)

    expect(onFileSelect).toHaveBeenCalledTimes(1)
    expect(onFileSelect).toHaveBeenCalledWith(file)
  })
})
