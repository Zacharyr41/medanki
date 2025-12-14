import { ApiError, type Job, type PreviewResponse, type UploadOptions } from './types'

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export { ApiError }

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

export async function uploadFile(
  file: File,
  options?: UploadOptions
): Promise<{ jobId: string }> {
  const formData = new FormData()
  formData.append('file', file)

  if (options?.exam) {
    formData.append('exam', options.exam)
  }
  if (options?.cardTypes) {
    formData.append('cardTypes', options.cardTypes.join(','))
  }
  if (options?.maxCardsPerChunk !== undefined) {
    formData.append('maxCardsPerChunk', String(options.maxCardsPerChunk))
  }

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })

  return handleResponse<{ jobId: string }>(response)
}

export async function getJob(id: string): Promise<Job> {
  const response = await fetch(`${API_BASE_URL}/jobs/${id}`)
  return handleResponse<Job>(response)
}

export async function getJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE_URL}/jobs`)
  return handleResponse<Job[]>(response)
}

export async function getPreview(
  id: string,
  params?: { page?: number; limit?: number }
): Promise<PreviewResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page !== undefined) {
    searchParams.set('page', String(params.page))
  }
  if (params?.limit !== undefined) {
    searchParams.set('limit', String(params.limit))
  }

  const queryString = searchParams.toString()
  const url = `${API_BASE_URL}/jobs/${id}/preview${queryString ? `?${queryString}` : ''}`

  const response = await fetch(url)
  return handleResponse<PreviewResponse>(response)
}

export async function downloadDeck(id: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/jobs/${id}/download`)

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.error || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }

  return response.blob()
}

export async function cancelJob(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/jobs/${id}/cancel`, {
    method: 'POST',
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.error || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }
}
