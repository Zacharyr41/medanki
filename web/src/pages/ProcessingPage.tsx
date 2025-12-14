import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useWebSocket, type Stage } from '../hooks/useWebSocket'
import { ProgressBar } from '../components/ProgressBar'
import { StageList } from '../components/StageList'
import { ConfirmDialog } from '../components/ConfirmDialog'

const stageOrder: Stage[] = ['ingesting', 'chunking', 'classifying', 'generating', 'exporting']

function getCompletedStages(currentStage: Stage): Stage[] {
  const currentIndex = stageOrder.indexOf(currentStage)
  return stageOrder.slice(0, currentIndex)
}

export function ProcessingPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { progress, stage, status, error, fileName } = useWebSocket(id!)

  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [stageTimes] = useState<Partial<Record<Stage, number>>>({})

  useEffect(() => {
    if (status === 'complete') {
      navigate(`/download/${id}`)
    }
  }, [status, id, navigate])

  const handleCancel = () => {
    setShowCancelDialog(true)
  }

  const handleConfirmCancel = () => {
    navigate('/')
  }

  if (status === 'error') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Processing Failed</h2>
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Processing Your File</h2>
        {fileName && (
          <p className="text-gray-600 mb-6">
            Processing: <span className="font-medium">{fileName}</span>
          </p>
        )}

        <div className="mb-8">
          <ProgressBar progress={progress} stage={stage} />
        </div>

        <div className="mb-8">
          <StageList
            currentStage={stage}
            completedStages={getCompletedStages(stage)}
            stageTimes={stageTimes}
          />
        </div>

        <div className="flex justify-center">
          <button
            onClick={handleCancel}
            className="px-6 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>

      {showCancelDialog && (
        <ConfirmDialog
          title="Cancel Processing?"
          message="Are you sure you want to cancel? Your progress will be lost."
          onConfirm={handleConfirmCancel}
          onCancel={() => setShowCancelDialog(false)}
        />
      )}
    </div>
  )
}
