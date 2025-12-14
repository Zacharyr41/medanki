import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileUpload } from '../components/FileUpload'
import { OptionsPanel, type GenerationOptions } from '../components/OptionsPanel'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { uploadFile } from '../api/upload'

const DEFAULT_OPTIONS: GenerationOptions = {
  exam: 'USMLE Step 1',
  cardTypes: { cloze: true, vignette: true },
  maxCards: 10,
}

export function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [options, setOptions] = useState<GenerationOptions>(DEFAULT_OPTIONS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    try {
      const response = await uploadFile(file, options)
      navigate(`/processing/${response.jobId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-page">
      <h1>Generate Flashcards</h1>

      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

      <FileUpload onFileSelect={setFile} />

      <OptionsPanel options={options} onChange={setOptions} />

      <Button
        variant="primary"
        disabled={!file}
        loading={loading}
        onClick={handleSubmit}
      >
        Generate Cards
      </Button>
    </div>
  )
}
