import type { GenerationOptions } from '../components/OptionsPanel'

interface UploadResponse {
  jobId: string
}

export async function uploadFile(
  file: File,
  options: GenerationOptions
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('options', JSON.stringify(options))

  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Upload failed')
  }

  return response.json()
}
