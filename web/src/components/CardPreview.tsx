import type { CardPreview as CardPreviewType } from '../types'
import { Chip } from './Chip'

interface CardPreviewProps {
  card: CardPreviewType
  expanded?: boolean
  onToggle?: (id: string) => void
}

function highlightCloze(text: string) {
  const parts = text.split(/(\{\{c\d+::[^}]+\}\})/g)
  return parts.map((part, index) => {
    const match = part.match(/\{\{c\d+::([^}]+)\}\}/)
    if (match) {
      return (
        <span key={index} data-testid="cloze-highlight" className="bg-yellow-200 px-1 rounded">
          {match[1]}
        </span>
      )
    }
    return part
  })
}

export function CardPreview({ card, expanded = false, onToggle }: CardPreviewProps) {
  const isCloze = card.type === 'cloze'
  const isVignette = card.type === 'vignette'

  return (
    <div data-testid="card-preview" className="border rounded-lg p-4 mb-4">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <span className="text-xs uppercase text-gray-500 font-medium">
            {card.type}
          </span>
          <div className="mt-2">
            {isCloze ? (
              <p className="text-gray-900">{highlightCloze(card.text)}</p>
            ) : (
              <p className="text-gray-900">{card.front || card.text}</p>
            )}
          </div>
        </div>
        {onToggle && (
          <button
            data-testid="expand-button"
            onClick={() => onToggle(card.id)}
            className="ml-4 text-blue-600 hover:text-blue-800"
          >
            {expanded ? '−' : '+'}
          </button>
        )}
      </div>

      {isVignette && expanded && (
        <div className="mt-4 space-y-2 border-t pt-4">
          {card.answer && (
            <div>
              <span className="font-medium">Answer:</span> {card.answer}
            </div>
          )}
          {card.explanation && (
            <div>
              <span className="font-medium">Explanation:</span> {card.explanation}
            </div>
          )}
          {card.distinguishing_feature && (
            <div>
              <span className="font-medium">Key Feature:</span> {card.distinguishing_feature}
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {card.tags.map((tag) => (
          <Chip key={tag} label={tag} testId={`tag-${tag}`} />
        ))}
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {card.topics.map((topic) => (
          <Chip key={topic} label={topic} variant="primary" testId={`topic-${topic}`} />
        ))}
      </div>

      {card.source && (
        <div data-testid="card-source" className="mt-4 text-sm text-gray-500">
          Source: {card.source}
        </div>
      )}
    </div>
  )
}
