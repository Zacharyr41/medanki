import { API_BASE_URL } from './client'

const API_BASE = `${API_BASE_URL}/api`

export async function downloadDeck(jobId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/download`)
  if (!response.ok) {
    throw new Error('Failed to download deck')
  }
  return response.blob()
}

export async function regenerateDeck(jobId: string): Promise<{ job_id: string }> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    throw new Error('Failed to regenerate deck')
  }
  return response.json()
}
