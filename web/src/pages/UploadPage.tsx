import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileUpload } from '../components/FileUpload'
import { InputModeSelector, type InputMode } from '../components/InputModeSelector'
import { TopicInput } from '../components/TopicInput'
import { OptionsPanel, type GenerationOptions } from '../components/OptionsPanel'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { uploadFile, uploadWithTopic } from '../api/upload'

const DEFAULT_OPTIONS: GenerationOptions = {
  exam: 'MCAT',
  cardTypes: { cloze: true, vignette: true },
  maxCards: 20,
}

export function UploadPage() {
  const navigate = useNavigate()
  const [inputMode, setInputMode] = useState<InputMode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [topicText, setTopicText] = useState('')
  const [options, setOptions] = useState<GenerationOptions>(DEFAULT_OPTIONS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit =
    inputMode === 'file' ? file !== null : topicText.trim().length > 0

  const handleSubmit = async () => {
    if (!canSubmit) return

    setLoading(true)
    setError(null)

    try {
      let response
      if (inputMode === 'file' && file) {
        response = await uploadFile(file, options)
      } else if (inputMode === 'topic') {
        response = await uploadWithTopic(topicText, options)
      } else {
        throw new Error('Invalid input')
      }
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

      <InputModeSelector mode={inputMode} onChange={setInputMode} />

      {inputMode === 'file' ? (
        <FileUpload onFileSelect={setFile} />
      ) : (
        <TopicInput value={topicText} onChange={setTopicText} />
      )}

      <OptionsPanel options={options} onChange={setOptions} />

      <Button
        variant="primary"
        disabled={!canSubmit}
        loading={loading}
        onClick={handleSubmit}
      >
        Generate Cards
      </Button>
    </div>
  )
}
