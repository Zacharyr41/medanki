import { useCallback } from 'react'

interface TopicInputProps {
  value: string
  onChange: (value: string) => void
  maxLength?: number
}

const DEFAULT_MAX_LENGTH = 2000

export function TopicInput({
  value,
  onChange,
  maxLength = DEFAULT_MAX_LENGTH,
}: TopicInputProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value
      if (newValue.length <= maxLength) {
        onChange(newValue)
      } else {
        onChange(newValue.slice(0, maxLength))
      }
    },
    [onChange, maxLength]
  )

  return (
    <div className="topic-input-container">
      <textarea
        data-testid="topic-input"
        className="topic-input"
        value={value}
        onChange={handleChange}
        placeholder="Describe the topics you want to study. For example: 'I want to learn about cardiac electrophysiology, including action potentials, arrhythmias, and treatment options.'"
        rows={6}
      />
      <div className="topic-input-footer">
        <span data-testid="char-count" className="char-count">
          {value.length}
        </span>
        <span className="char-limit">/ {maxLength}</span>
      </div>
    </div>
  )
}
