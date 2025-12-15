import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProgressBar } from '../ProgressBar'

describe('ProgressBar', () => {
  it('shows percentage', () => {
    render(<ProgressBar progress={50} stage="chunking" />)

    expect(screen.getByText('50.0%')).toBeInTheDocument()
  })

  it('fills to percentage', () => {
    render(<ProgressBar progress={75} stage="classifying" />)

    const bar = screen.getByTestId('progress-fill')
    expect(bar).toHaveStyle({ width: '75%' })
  })

  it('shows stage', () => {
    render(<ProgressBar progress={30} stage="ingesting" />)

    expect(screen.getByText(/ingesting/i)).toBeInTheDocument()
  })

  it('has animation class', () => {
    render(<ProgressBar progress={60} stage="generating" />)

    const bar = screen.getByTestId('progress-fill')
    expect(bar).toHaveClass('transition-all')
  })
})
