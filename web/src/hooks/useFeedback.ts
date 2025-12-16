import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  submitFeedback,
  submitCorrection,
  getCardFeedbackAggregate,
  getCardFeedbackHistory,
} from '../api/feedback'
import type { FeedbackRequest, CorrectionRequest } from '../types'

export function useFeedbackMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: FeedbackRequest) => submitFeedback(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['feedback', variables.card_id],
      })
    },
  })
}

export function useCorrectionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CorrectionRequest) => submitCorrection(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['feedback', variables.card_id],
      })
    },
  })
}

export function useCardFeedbackQuery(cardId: string | null) {
  return useQuery({
    queryKey: ['feedback', cardId],
    queryFn: () => getCardFeedbackAggregate(cardId!),
    enabled: !!cardId,
  })
}

export function useCardFeedbackHistoryQuery(cardId: string | null) {
  return useQuery({
    queryKey: ['feedback', cardId, 'history'],
    queryFn: () => getCardFeedbackHistory(cardId!),
    enabled: !!cardId,
  })
}
