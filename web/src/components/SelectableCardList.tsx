import { useEffect, useRef } from 'react'
import { CardPreview } from './CardPreview'
import type { CardPreview as CardPreviewType } from '../types'

interface SelectableCardListProps {
  cards: CardPreviewType[]
  selectedIds: string[]
  onSelectionChange: (selectedIds: string[]) => void
}

export function SelectableCardList({
  cards,
  selectedIds,
  onSelectionChange,
}: SelectableCardListProps) {
  const selectAllRef = useRef<HTMLInputElement>(null)

  const allSelected = cards.length > 0 && selectedIds.length === cards.length
  const someSelected = selectedIds.length > 0 && selectedIds.length < cards.length

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected
    }
  }, [someSelected])

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange(cards.map((card) => card.id))
    }
  }

  const handleSelectCard = (cardId: string) => {
    if (selectedIds.includes(cardId)) {
      onSelectionChange(selectedIds.filter((id) => id !== cardId))
    } else {
      onSelectionChange([...selectedIds, cardId])
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            ref={selectAllRef}
            type="checkbox"
            data-testid="select-all-checkbox"
            checked={allSelected}
            onChange={handleSelectAll}
            className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="font-medium">
            Select all ({cards.length} cards)
          </span>
        </label>
        {selectedIds.length > 0 && (
          <span className="text-sm text-gray-600">
            {selectedIds.length} selected
          </span>
        )}
      </div>

      <div className="space-y-2">
        {cards.map((card) => (
          <div
            key={card.id}
            className={`flex items-start gap-3 p-3 border rounded-lg transition-colors ${
              selectedIds.includes(card.id)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <input
              type="checkbox"
              data-testid={`card-checkbox-${card.id}`}
              checked={selectedIds.includes(card.id)}
              onChange={() => handleSelectCard(card.id)}
              className="mt-1 w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1 min-w-0">
              <CardPreview card={card} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
