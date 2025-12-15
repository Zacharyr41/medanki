import type { PreviewResponse, StatsResponse } from '../types'
import { API_BASE_URL } from './client'

const API_BASE = `${API_BASE_URL}/api`

export interface FetchPreviewParams {
  jobId: string
  limit?: number
  offset?: number
  type?: string
  topic?: string
}

export async function fetchPreview(params: FetchPreviewParams): Promise<PreviewResponse> {
  const { jobId, limit = 20, offset = 0, type, topic } = params
  const searchParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  if (type) searchParams.set('type', type)
  if (topic) searchParams.set('topic', topic)

  const response = await fetch(`${API_BASE}/jobs/${jobId}/preview?${searchParams}`)
  if (!response.ok) {
    throw new Error('Failed to fetch preview')
  }
  return response.json()
}

export async function fetchStats(jobId: string): Promise<StatsResponse> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/stats`)
  if (!response.ok) {
    throw new Error('Failed to fetch stats')
  }
  return response.json()
}
