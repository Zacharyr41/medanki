import type { Stage } from '../hooks/useWebSocket'

interface ProgressBarProps {
  progress: number
  stage: Stage
}

const stageLabels: Record<Stage, string> = {
  ingesting: 'Ingesting',
  chunking: 'Chunking',
  classifying: 'Classifying',
  generating: 'Generating',
  exporting: 'Exporting',
}

export function ProgressBar({ progress, stage }: ProgressBarProps) {
  return (
    <div data-testid="progress-bar" className="w-full">
      <div className="flex justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {stageLabels[stage]}
        </span>
        <span className="text-sm font-medium text-gray-700">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div
          data-testid="progress-fill"
          className="h-full bg-blue-600 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
