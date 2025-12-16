import { API_BASE_URL, ApiError } from './client'
import type {
  FeedbackRequest,
  FeedbackResponse,
  CorrectionRequest,
  ImplicitSignalRequest,
  FeedbackAggregate,
} from '../types'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.error || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }
  return response.json()
}

export async function submitFeedback(
  request: FeedbackRequest
): Promise<FeedbackResponse> {
  const response = await fetch(`${API_BASE_URL}/api/feedback/explicit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return handleResponse<FeedbackResponse>(response)
}

export async function submitCorrection(
  request: CorrectionRequest
): Promise<{ id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/feedback/correction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return handleResponse<{ id: string }>(response)
}

export async function submitImplicitSignal(
  request: ImplicitSignalRequest
): Promise<{ id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/feedback/implicit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return handleResponse<{ id: string }>(response)
}

export async function getCardFeedbackAggregate(
  cardId: string
): Promise<FeedbackAggregate> {
  const response = await fetch(`${API_BASE_URL}/api/feedback/cards/${cardId}`)
  return handleResponse<FeedbackAggregate>(response)
}

export async function getCardFeedbackHistory(
  cardId: string
): Promise<FeedbackResponse[]> {
  const response = await fetch(`${API_BASE_URL}/api/feedback/cards/${cardId}/history`)
  return handleResponse<FeedbackResponse[]>(response)
}
