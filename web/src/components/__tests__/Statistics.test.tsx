import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Statistics } from '../Statistics'
import type { StatsResponse } from '../../types'

describe('Statistics', () => {
  const mockStats: StatsResponse = {
    counts: {
      total: 100,
      cloze: 60,
      vignette: 35,
      basic_qa: 5,
    },
    topics: {
      cardiology: 30,
      neurology: 25,
      anatomy: 20,
      physiology: 15,
      emergency: 10,
    },
    timing: {
      created_at: '2024-01-15T10:00:00Z',
      completed_at: '2024-01-15T10:05:30Z',
      duration_seconds: 330,
    },
  }

  it('test_shows_total_cards - Total card count', () => {
    render(<Statistics stats={mockStats} />)

    expect(screen.getByTestId('total-cards')).toBeInTheDocument()
    expect(screen.getByTestId('total-cards')).toHaveTextContent('100')
  })

  it('test_shows_by_type - Breakdown by card type', () => {
    render(<Statistics stats={mockStats} />)

    expect(screen.getByTestId('type-breakdown')).toBeInTheDocument()
    expect(screen.getByTestId('cloze-count')).toHaveTextContent('60')
    expect(screen.getByTestId('vignette-count')).toHaveTextContent('35')
    expect(screen.getByTestId('basic-qa-count')).toHaveTextContent('5')
  })

  it('test_shows_by_topic - Topic distribution chart', () => {
    render(<Statistics stats={mockStats} />)

    const topicSection = screen.getByTestId('topic-distribution')
    expect(topicSection).toBeInTheDocument()
    expect(screen.getByText(/cardiology/i)).toBeInTheDocument()
    expect(topicSection).toHaveTextContent('30')
  })

  it('test_shows_processing_time - Duration displayed', () => {
    render(<Statistics stats={mockStats} />)

    expect(screen.getByTestId('processing-time')).toBeInTheDocument()
    expect(screen.getByTestId('processing-time')).toHaveTextContent(/5.*30|330/i)
  })
})
