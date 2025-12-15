import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { InputModeSelector } from '../InputModeSelector'

describe('InputModeSelector', () => {
  it('renders file and topic tabs', () => {
    render(<InputModeSelector mode="file" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: 'Upload File' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Describe Topics' })).toBeInTheDocument()
  })

  it('marks file tab as selected when mode is file', () => {
    render(<InputModeSelector mode="file" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: 'Upload File' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    expect(screen.getByRole('tab', { name: 'Describe Topics' })).toHaveAttribute(
      'aria-selected',
      'false'
    )
  })

  it('marks topic tab as selected when mode is topic', () => {
    render(<InputModeSelector mode="topic" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: 'Upload File' })).toHaveAttribute(
      'aria-selected',
      'false'
    )
    expect(screen.getByRole('tab', { name: 'Describe Topics' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  it('calls onChange with file when file tab is clicked', async () => {
    const onChange = vi.fn()
    render(<InputModeSelector mode="topic" onChange={onChange} />)

    await userEvent.click(screen.getByRole('tab', { name: 'Upload File' }))

    expect(onChange).toHaveBeenCalledWith('file')
  })

  it('calls onChange with topic when topic tab is clicked', async () => {
    const onChange = vi.fn()
    render(<InputModeSelector mode="file" onChange={onChange} />)

    await userEvent.click(screen.getByRole('tab', { name: 'Describe Topics' }))

    expect(onChange).toHaveBeenCalledWith('topic')
  })

  it('has active class on selected tab', () => {
    render(<InputModeSelector mode="file" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: 'Upload File' })).toHaveClass('active')
    expect(screen.getByRole('tab', { name: 'Describe Topics' })).not.toHaveClass('active')
  })
})
