import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { fetchStats } from '../api/preview'
import { downloadDeck, regenerateDeck } from '../api/download'
import { Statistics } from '../components/Statistics'
import { CardList } from '../components/CardList'

export function DownloadPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', jobId],
    queryFn: () => fetchStats(jobId!),
    enabled: !!jobId,
  })

  const downloadMutation = useMutation({
    mutationFn: () => downloadDeck(jobId!),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `medanki_${jobId}.apkg`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
  })

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateDeck(jobId!),
    onSuccess: (data) => {
      navigate(`/download/${data.job_id}`)
    },
  })

  if (!jobId) {
    return <div>Invalid job ID</div>
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Download Your Deck</h1>
        <div className="flex gap-4">
          <Link
            to="/"
            data-testid="upload-link"
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            Upload Another
          </Link>
          <button
            data-testid="regenerate-button"
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending}
            className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            {regenerateMutation.isPending ? 'Regenerating...' : 'Regenerate'}
          </button>
          <button
            data-testid="download-button"
            onClick={() => downloadMutation.mutate()}
            disabled={downloadMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {downloadMutation.isPending ? 'Downloading...' : 'Download .apkg'}
          </button>
        </div>
      </div>

      {statsLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      ) : stats ? (
        <Statistics stats={stats} />
      ) : null}

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Card Preview</h2>
        <CardList jobId={jobId} />
      </div>
    </div>
  )
}
