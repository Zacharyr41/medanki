import { useState, useCallback, useRef } from 'react'

interface FileUploadProps {
  onFileSelect: (file: File | null) => void
  acceptedTypes?: string[]
  maxSizeMB?: number
}

const DEFAULT_ACCEPTED_TYPES = [
  'application/pdf',
  'text/markdown',
  'text/x-markdown',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
const DEFAULT_ACCEPTED_EXTENSIONS = ['.pdf', '.md', '.txt', '.docx']

export function FileUpload({
  onFileSelect,
  acceptedTypes = DEFAULT_ACCEPTED_TYPES,
  maxSizeMB = 50,
}: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const validateFile = useCallback(
    (file: File): boolean => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()
      const isValidType =
        acceptedTypes.includes(file.type) ||
        DEFAULT_ACCEPTED_EXTENSIONS.includes(extension)

      if (!isValidType) {
        setError('Unsupported file type. Please upload a PDF, Markdown, TXT, or DOCX file.')
        return false
      }

      const maxBytes = maxSizeMB * 1024 * 1024
      if (file.size > maxBytes) {
        setError(`File too large. Maximum size is ${maxSizeMB}MB.`)
        return false
      }

      return true
    },
    [acceptedTypes, maxSizeMB]
  )

  const handleFileChange = useCallback(
    (file: File | null) => {
      setError(null)

      if (!file) {
        setSelectedFile(null)
        onFileSelect(null)
        return
      }

      if (validateFile(file)) {
        setSelectedFile(file)
        onFileSelect(file)
      }
    },
    [validateFile, onFileSelect]
  )

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    handleFileChange(file)
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragActive(false)
      const file = e.dataTransfer.files[0] || null
      handleFileChange(file)
    },
    [handleFileChange]
  )

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleRemove = () => {
    setSelectedFile(null)
    setError(null)
    onFileSelect(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const handleClick = () => {
    inputRef.current?.click()
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="file-upload">
      <div
        data-testid="dropzone"
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
        onDrop={handleDrop}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onClick={handleClick}
      >
        <input
          ref={inputRef}
          type="file"
          data-testid="file-input"
          accept=".pdf,.md,.txt,.docx"
          onChange={handleInputChange}
          style={{ display: 'none' }}
        />

        {selectedFile ? (
          <div className="file-preview">
            <div className="file-info">
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">{formatFileSize(selectedFile.size)}</span>
            </div>
            <button
              type="button"
              className="remove-button"
              onClick={(e) => {
                e.stopPropagation()
                handleRemove()
              }}
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="dropzone-content">
            <p>Drop your file here or click to browse</p>
            <p className="supported-formats">Supported: PDF, Markdown, TXT, DOCX</p>
          </div>
        )}
      </div>

      {error && <p className="error-message">{error}</p>}
    </div>
  )
}
