import { useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { saveCards } from '../api/savedCards'

interface SaveCardsButtonProps {
  jobId: string
  selectedCardIds: string[]
  onSaved: () => void
}

export function SaveCardsButton({
  jobId,
  selectedCardIds,
  onSaved,
}: SaveCardsButtonProps) {
  const { isAuthenticated } = useAuthStore()
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const handleClick = async () => {
    if (!isAuthenticated) {
      setShowLoginPrompt(true)
      return
    }

    setIsSaving(true)
    setSuccessMessage(null)

    try {
      const result = await saveCards({
        job_id: jobId,
        card_ids: selectedCardIds,
      })
      setSuccessMessage(result.message)
      onSaved()
    } catch (error) {
      console.error('Failed to save cards:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const isDisabled = selectedCardIds.length === 0 || isSaving

  return (
    <div className="space-y-2">
      <button
        data-testid="save-cards-button"
        onClick={handleClick}
        disabled={isDisabled}
        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
          isDisabled
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {isSaving
          ? 'Saving...'
          : `Save ${selectedCardIds.length} Card${selectedCardIds.length !== 1 ? 's' : ''}`}
      </button>

      {showLoginPrompt && (
        <div
          data-testid="login-prompt"
          className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800"
        >
          Please sign in with Google to save cards to your account.
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          {successMessage}
        </div>
      )}
    </div>
  )
}
