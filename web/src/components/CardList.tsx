import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPreview } from '../api/preview'
import { CardPreview } from './CardPreview'

interface CardListProps {
  jobId: string
}

export function CardList({ jobId }: CardListProps) {
  const [offset, setOffset] = useState(0)
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [expandedCard, setExpandedCard] = useState<string | null>(null)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['preview', jobId, offset, typeFilter],
    queryFn: () =>
      fetchPreview({
        jobId,
        limit,
        offset,
        type: typeFilter || undefined,
      }),
  })

  const handleToggle = (cardId: string) => {
    setExpandedCard(expandedCard === cardId ? null : cardId)
  }

  if (isLoading) {
    return (
      <div data-testid="loading-skeleton" className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (!data || data.cards.length === 0) {
    return (
      <div data-testid="empty-state" className="text-center py-8 text-gray-500">
        No cards found
      </div>
    )
  }

  const totalPages = Math.ceil(data.total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div data-testid="card-list">
      <div className="mb-4 flex items-center gap-4">
        <select
          data-testid="type-filter"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value)
            setOffset(0)
          }}
          className="border rounded px-3 py-2"
        >
          <option value="">All Types</option>
          <option value="cloze">Cloze</option>
          <option value="vignette">Vignette</option>
          <option value="basic_qa">Basic Q&A</option>
        </select>
      </div>

      <div className="space-y-4">
        {data.cards.map((card) => (
          <CardPreview
            key={card.id}
            card={card}
            expanded={expandedCard === card.id}
            onToggle={handleToggle}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div data-testid="pagination" className="mt-6 flex items-center justify-center gap-4">
          <button
            data-testid="prev-page"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span data-testid="page-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            data-testid="next-page"
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= data.total}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
