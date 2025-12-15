import { API_BASE_URL, ApiError } from './client'
import { useAuthStore } from '../stores/authStore'

export interface SavedCard {
  id: string
  card_id: string
  job_id: string
  saved_at: string
}

export interface SavedCardsResponse {
  cards: SavedCard[]
  total: number
  limit: number
  offset: number
}

export interface SaveCardsRequest {
  job_id: string
  card_ids: string[]
}

export interface SaveCardsResponse {
  saved_count: number
  message: string
}

function getAuthHeaders(): HeadersInit {
  const token = useAuthStore.getState().token
  if (!token) throw new ApiError('Not authenticated', 401, 'unauthorized')
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    useAuthStore.getState().logout()
    throw new ApiError('Unauthorized', 401, 'unauthorized')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.detail || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }
  return response.json()
}

export async function saveCards(request: SaveCardsRequest): Promise<SaveCardsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/saved-cards`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  })

  return handleResponse<SaveCardsResponse>(response)
}

export async function getSavedCards(
  limit: number = 20,
  offset: number = 0
): Promise<SavedCardsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/saved-cards?limit=${limit}&offset=${offset}`,
    { headers: getAuthHeaders() }
  )

  return handleResponse<SavedCardsResponse>(response)
}

export async function removeSavedCard(cardId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/saved-cards/${cardId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.detail || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }
}

export async function exportSavedCards(): Promise<Blob> {
  const token = useAuthStore.getState().token
  if (!token) throw new ApiError('Not authenticated', 401, 'unauthorized')

  const response = await fetch(`${API_BASE_URL}/api/saved-cards/export`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (response.status === 401) {
    useAuthStore.getState().logout()
    throw new ApiError('Unauthorized', 401, 'unauthorized')
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.detail || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }

  return response.blob()
}
