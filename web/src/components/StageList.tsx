import type { Stage } from '../hooks/useWebSocket'

interface StageListProps {
  currentStage: Stage
  completedStages: Stage[]
  stageTimes: Partial<Record<Stage, number>>
}

const stages: { id: Stage; label: string }[] = [
  { id: 'ingesting', label: 'Ingesting' },
  { id: 'chunking', label: 'Chunking' },
  { id: 'classifying', label: 'Classifying' },
  { id: 'generating', label: 'Generating' },
  { id: 'exporting', label: 'Exporting' },
]

function CheckIcon() {
  return (
    <svg
      data-testid="check-icon"
      className="w-5 h-5 text-green-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg
      className="w-5 h-5 text-blue-600 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

function PendingIcon() {
  return (
    <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
  )
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  return `${seconds}s`
}

export function StageList({ currentStage, completedStages, stageTimes }: StageListProps) {
  return (
    <div data-testid="stage-list" className="space-y-3">
      {stages.map(({ id, label }) => {
        const isCompleted = completedStages.includes(id)
        const isCurrent = currentStage === id
        const duration = stageTimes[id]

        return (
          <div
            key={id}
            data-testid={`stage-${id}`}
            className={`flex items-center justify-between p-3 rounded-lg ${
              isCurrent
                ? 'bg-blue-50 text-blue-600'
                : isCompleted
                ? 'bg-green-50 text-green-700'
                : 'bg-gray-50 text-gray-500'
            }`}
          >
            <div className="flex items-center gap-3">
              {isCompleted ? (
                <CheckIcon />
              ) : isCurrent ? (
                <SpinnerIcon />
              ) : (
                <PendingIcon />
              )}
              <span className="font-medium">{label}</span>
            </div>
            {duration !== undefined && (
              <span className="text-sm">{formatDuration(duration)}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
