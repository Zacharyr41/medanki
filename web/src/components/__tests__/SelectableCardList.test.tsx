import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SelectableCardList } from '../SelectableCardList'

const mockCards = [
  {
    id: 'card1',
    type: 'cloze' as const,
    text: 'The {{c1::mitochondria}} is the powerhouse of the cell.',
    tags: ['biology'],
    topics: [{ id: 'bio1', title: 'Cell Biology' }],
  },
  {
    id: 'card2',
    type: 'cloze' as const,
    text: '{{c1::ATP}} is the primary energy currency.',
    tags: ['biochemistry'],
    topics: [{ id: 'biochem1', title: 'Biochemistry' }],
  },
  {
    id: 'card3',
    type: 'vignette' as const,
    text: 'A 45-year-old patient presents with...',
    tags: ['clinical'],
    topics: [{ id: 'cardio1', title: 'Cardiology' }],
    front: 'A 45-year-old patient presents with...',
    answer: 'Myocardial infarction',
    explanation: 'This is a classic presentation of MI.',
  },
]

describe('SelectableCardList', () => {
  it('renders checkbox for each card', () => {
    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={[]}
        onSelectionChange={() => {}}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(mockCards.length + 1)
  })

  it('calls onSelectionChange when card is selected', () => {
    const onSelectionChange = vi.fn()

    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
      />
    )

    const checkboxes = screen.getAllByTestId(/card-checkbox-/)
    fireEvent.click(checkboxes[0])

    expect(onSelectionChange).toHaveBeenCalledWith(['card1'])
  })

  it('calls onSelectionChange when card is deselected', () => {
    const onSelectionChange = vi.fn()

    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={['card1', 'card2']}
        onSelectionChange={onSelectionChange}
      />
    )

    const checkboxes = screen.getAllByTestId(/card-checkbox-/)
    fireEvent.click(checkboxes[0])

    expect(onSelectionChange).toHaveBeenCalledWith(['card2'])
  })

  it('selects all cards when select all is clicked', () => {
    const onSelectionChange = vi.fn()

    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
      />
    )

    const selectAllCheckbox = screen.getByTestId('select-all-checkbox')
    fireEvent.click(selectAllCheckbox)

    expect(onSelectionChange).toHaveBeenCalledWith(['card1', 'card2', 'card3'])
  })

  it('deselects all cards when select all is unchecked', () => {
    const onSelectionChange = vi.fn()

    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={['card1', 'card2', 'card3']}
        onSelectionChange={onSelectionChange}
      />
    )

    const selectAllCheckbox = screen.getByTestId('select-all-checkbox')
    fireEvent.click(selectAllCheckbox)

    expect(onSelectionChange).toHaveBeenCalledWith([])
  })

  it('displays selection count', () => {
    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={['card1', 'card2']}
        onSelectionChange={() => {}}
      />
    )

    expect(screen.getByText(/2 selected/i)).toBeInTheDocument()
  })

  it('shows indeterminate state when some cards selected', () => {
    render(
      <SelectableCardList
        cards={mockCards}
        selectedIds={['card1']}
        onSelectionChange={() => {}}
      />
    )

    const selectAllCheckbox = screen.getByTestId('select-all-checkbox') as HTMLInputElement
    expect(selectAllCheckbox.indeterminate).toBe(true)
  })
})
