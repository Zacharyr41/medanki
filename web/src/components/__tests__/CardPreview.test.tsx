import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CardPreview } from '../CardPreview'
import type { CardPreview as CardPreviewType } from '../../types'

describe('CardPreview', () => {
  const mockClozeCard: CardPreviewType = {
    id: 'card-1',
    type: 'cloze',
    text: 'The {{c1::mitochondria}} is the powerhouse of the cell.',
    tags: ['biology', 'cell-biology'],
    topics: ['1A', '1B'],
    status: 'pending',
    source: 'Chapter 1, Page 5',
  }

  const mockVignetteCard: CardPreviewType = {
    id: 'card-2',
    type: 'vignette',
    text: 'A 45-year-old man presents with chest pain...',
    tags: ['cardiology', 'emergency'],
    topics: ['2A'],
    status: 'pending',
    source: 'Case Study 1',
    front: 'A 45-year-old man presents with chest pain...',
    answer: 'Myocardial infarction',
    explanation: 'The presentation is classic for MI with radiating pain.',
    distinguishing_feature: 'ST elevation on ECG',
  }

  it('test_renders_cloze_card - Cloze syntax highlighted', () => {
    render(<CardPreview card={mockClozeCard} />)

    expect(screen.getByTestId('card-preview')).toBeInTheDocument()
    expect(screen.getByTestId('cloze-highlight')).toBeInTheDocument()
    expect(screen.getByText(/mitochondria/)).toBeInTheDocument()
  })

  it('test_renders_vignette_card - All vignette fields shown', () => {
    render(<CardPreview card={mockVignetteCard} expanded />)

    expect(screen.getByTestId('card-preview')).toBeInTheDocument()
    expect(screen.getByText(/45-year-old man/)).toBeInTheDocument()
    expect(screen.getByText(/Myocardial infarction/)).toBeInTheDocument()
    expect(screen.getByText(/ST elevation/)).toBeInTheDocument()
  })

  it('test_shows_tags - Tags displayed as chips', () => {
    render(<CardPreview card={mockClozeCard} />)

    expect(screen.getByTestId('tag-biology')).toBeInTheDocument()
    expect(screen.getByTestId('tag-cell-biology')).toBeInTheDocument()
  })

  it('test_shows_topics - Topic matches listed', () => {
    render(<CardPreview card={mockClozeCard} />)

    expect(screen.getByTestId('topic-1A')).toBeInTheDocument()
    expect(screen.getByTestId('topic-1B')).toBeInTheDocument()
  })

  it('test_expandable - Click expands full details', () => {
    const onToggle = vi.fn()
    render(<CardPreview card={mockVignetteCard} expanded={false} onToggle={onToggle} />)

    const expandButton = screen.getByTestId('expand-button')
    fireEvent.click(expandButton)

    expect(onToggle).toHaveBeenCalledWith('card-2')
  })

  it('test_shows_source - Source chunk reference', () => {
    render(<CardPreview card={mockClozeCard} />)

    expect(screen.getByTestId('card-source')).toBeInTheDocument()
    expect(screen.getByText(/Chapter 1, Page 5/)).toBeInTheDocument()
  })
})
