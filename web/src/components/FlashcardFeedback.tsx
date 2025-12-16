import { useState, useCallback } from 'react'
import type { FeedbackType, FeedbackCategory } from '../types'

interface FlashcardFeedbackProps {
  cardId: string
  cardText?: string
  topicId?: string
  onFeedback: (data: {
    cardId: string
    feedbackType: FeedbackType
    categories: FeedbackCategory[]
    comment: string
  }) => void
  disabled?: boolean
}

const FEEDBACK_OPTIONS: { id: FeedbackCategory; label: string }[] = [
  { id: 'inaccurate', label: 'Medically inaccurate' },
  { id: 'unclear', label: 'Question unclear' },
  { id: 'wrong_answer', label: 'Answer incomplete/wrong' },
  { id: 'wrong_topic', label: 'Wrong topic classification' },
  { id: 'too_complex', label: 'Too many concepts' },
  { id: 'too_simple', label: 'Too simple/obvious' },
  { id: 'duplicate', label: 'Duplicate card' },
]

export function FlashcardFeedback({
  cardId,
  onFeedback,
  disabled = false,
}: FlashcardFeedbackProps) {
  const [rating, setRating] = useState<FeedbackType | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<FeedbackCategory[]>([])
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleQuickRating = useCallback(
    (feedbackType: FeedbackType) => {
      setRating(feedbackType)
      onFeedback({
        cardId,
        feedbackType,
        categories: [],
        comment: '',
      })
      setSubmitted(true)
    },
    [cardId, onFeedback]
  )

  const handleDetailedFeedback = useCallback(() => {
    if (!rating) return
    onFeedback({
      cardId,
      feedbackType: rating,
      categories: selectedCategories,
      comment,
    })
    setShowDetails(false)
    setSubmitted(true)
  }, [cardId, rating, selectedCategories, comment, onFeedback])

  const toggleCategory = (category: FeedbackCategory) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <span>Thanks for your feedback!</span>
        <button
          onClick={() => {
            setSubmitted(false)
            setRating(null)
            setSelectedCategories([])
            setComment('')
          }}
          className="text-blue-600 hover:underline"
        >
          Change
        </button>
      </div>
    )
  }

  return (
    <div data-testid="flashcard-feedback" className="mt-4">
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-600">Rate this card:</span>
        <button
          data-testid="thumbs-up"
          onClick={() => handleQuickRating('thumbs_up')}
          disabled={disabled}
          className={`p-2 rounded-full transition-colors ${
            rating === 'thumbs_up'
              ? 'bg-green-100 text-green-600'
              : 'hover:bg-gray-100 text-gray-400'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          aria-label="Thumbs up"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
            />
          </svg>
        </button>
        <button
          data-testid="thumbs-down"
          onClick={() => {
            setRating('thumbs_down')
            setShowDetails(true)
          }}
          disabled={disabled}
          className={`p-2 rounded-full transition-colors ${
            rating === 'thumbs_down'
              ? 'bg-red-100 text-red-600'
              : 'hover:bg-gray-100 text-gray-400'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          aria-label="Thumbs down"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
            />
          </svg>
        </button>
        <button
          data-testid="details-button"
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:underline ml-2"
        >
          {showDetails ? 'Hide details' : 'Add details'}
        </button>
      </div>

      {showDetails && (
        <div
          data-testid="feedback-details"
          className="mt-4 p-4 border rounded-lg bg-gray-50"
        >
          <h4 className="font-medium text-gray-900 mb-3">
            What's wrong with this card?
          </h4>
          <div className="space-y-2 mb-4">
            {FEEDBACK_OPTIONS.map((option) => (
              <label
                key={option.id}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedCategories.includes(option.id)}
                  onChange={() => toggleCategory(option.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{option.label}</span>
              </label>
            ))}
          </div>
          <textarea
            data-testid="feedback-comment"
            placeholder="Additional comments (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full p-2 border rounded-md text-sm resize-none"
            rows={3}
          />
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={() => setShowDetails(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              data-testid="submit-feedback"
              onClick={handleDetailedFeedback}
              disabled={!rating}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              Submit Feedback
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
