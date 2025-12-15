export interface GenerationOptions {
  exam: string
  cardTypes: {
    cloze: boolean
    vignette: boolean
  }
  maxCards: number
}

interface OptionsPanelProps {
  options: GenerationOptions
  onChange: (options: GenerationOptions) => void
}

const EXAM_OPTIONS = [
  { value: 'MCAT', label: 'MCAT' },
  { value: 'USMLE Step 1', label: 'USMLE Step 1' },
]

export function OptionsPanel({ options, onChange }: OptionsPanelProps) {
  const handleExamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...options, exam: e.target.value })
  }

  const handleCardTypeChange = (type: 'cloze' | 'vignette') => {
    onChange({
      ...options,
      cardTypes: { ...options.cardTypes, [type]: !options.cardTypes[type] },
    })
  }

  const handleMaxCardsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10)
    if (!isNaN(value) && value > 0) {
      onChange({ ...options, maxCards: value })
    }
  }

  return (
    <div className="options-panel">
      <div className="option-group">
        <label htmlFor="exam-select">Exam</label>
        <select
          id="exam-select"
          value={options.exam}
          onChange={handleExamChange}
        >
          {EXAM_OPTIONS.map((exam) => (
            <option key={exam.value} value={exam.value}>
              {exam.label}
            </option>
          ))}
        </select>
      </div>

      <div className="option-group">
        <span className="option-label">Card Types</span>
        <div className="checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={options.cardTypes.cloze}
              onChange={() => handleCardTypeChange('cloze')}
            />
            Cloze
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.cardTypes.vignette}
              onChange={() => handleCardTypeChange('vignette')}
            />
            Vignette
          </label>
        </div>
      </div>

      <div className="option-group">
        <label htmlFor="max-cards">Max Cards per Chunk</label>
        <input
          id="max-cards"
          type="number"
          min={1}
          max={50}
          value={options.maxCards}
          onChange={handleMaxCardsChange}
        />
      </div>
    </div>
  )
}
