import type { StatsResponse } from '../types'

interface StatisticsProps {
  stats: StatsResponse
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

export function Statistics({ stats }: StatisticsProps) {
  const topTopics = Object.entries(stats.topics)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)

  return (
    <div data-testid="statistics" className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="border rounded-lg p-4 text-center">
          <div data-testid="total-cards" className="text-3xl font-bold text-blue-600">
            {stats.counts.total}
          </div>
          <div className="text-sm text-gray-500">Total Cards</div>
        </div>

        <div data-testid="type-breakdown" className="border rounded-lg p-4">
          <div className="text-sm font-medium mb-2">By Type</div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Cloze</span>
              <span data-testid="cloze-count">{stats.counts.cloze}</span>
            </div>
            <div className="flex justify-between">
              <span>Vignette</span>
              <span data-testid="vignette-count">{stats.counts.vignette}</span>
            </div>
            <div className="flex justify-between">
              <span>Basic Q&A</span>
              <span data-testid="basic-qa-count">{stats.counts.basic_qa}</span>
            </div>
          </div>
        </div>

        <div data-testid="processing-time" className="border rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-600">
            {formatDuration(stats.timing.duration_seconds)}
          </div>
          <div className="text-sm text-gray-500">Processing Time</div>
        </div>
      </div>

      <div data-testid="topic-distribution" className="border rounded-lg p-4">
        <div className="text-sm font-medium mb-4">Top Topics</div>
        <div className="space-y-2">
          {topTopics.map(([topic, count]) => {
            const percentage = (count / stats.counts.total) * 100
            return (
              <div key={topic} className="flex items-center gap-2">
                <span className="w-24 text-sm truncate">{topic}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-500 h-4 rounded-full"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600 w-8">{count}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
