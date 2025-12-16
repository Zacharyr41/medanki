export type InputMode = 'file' | 'topic'

interface InputModeSelectorProps {
  mode: InputMode
  onChange: (mode: InputMode) => void
}

export function InputModeSelector({ mode, onChange }: InputModeSelectorProps) {
  return (
    <div className="input-mode-selector" role="tablist">
      <button
        role="tab"
        aria-selected={mode === 'file'}
        className={`mode-tab ${mode === 'file' ? 'active' : ''}`}
        onClick={() => onChange('file')}
      >
        Upload File
      </button>
      <button
        role="tab"
        aria-selected={mode === 'topic'}
        className={`mode-tab ${mode === 'topic' ? 'active' : ''}`}
        onClick={() => onChange('topic')}
      >
        Describe Topics
      </button>
    </div>
  )
}
