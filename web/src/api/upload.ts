import type { GenerationOptions } from '../components/OptionsPanel'
import { API_BASE_URL } from './client'

interface UploadResponse {
  jobId: string
}

interface ApiUploadResponse {
  job_id: string
  status: string
  created_at: string
}

function buildFormData(options: GenerationOptions): FormData {
  const formData = new FormData()
  formData.append('exam', options.exam)

  const cardTypes: string[] = []
  if (options.cardTypes.cloze) cardTypes.push('cloze')
  if (options.cardTypes.vignette) cardTypes.push('vignette')
  formData.append('card_types', cardTypes.join(','))
  formData.append('max_cards', String(options.maxCards))

  return formData
}

export async function uploadFile(
  file: File,
  options: GenerationOptions
): Promise<UploadResponse> {
  const formData = buildFormData(options)
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Upload failed')
  }

  const data: ApiUploadResponse = await response.json()
  return { jobId: data.job_id }
}

export async function uploadWithTopic(
  topicText: string,
  options: GenerationOptions
): Promise<UploadResponse> {
  const formData = buildFormData(options)
  formData.append('topic_text', topicText)

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || 'Upload failed')
  }

  const data: ApiUploadResponse = await response.json()
  return { jobId: data.job_id }
}
