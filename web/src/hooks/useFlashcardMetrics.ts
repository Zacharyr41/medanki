import { useEffect, useRef, useCallback } from 'react'
import { submitImplicitSignal } from '../api/feedback'

interface ImplicitMetrics {
  viewStartTime: number
  viewEndTime: number | null
  flipCount: number
  scrollDepth: number
  editAttempted: boolean
  copyAttempted: boolean
}

interface UseFlashcardMetricsOptions {
  enabled?: boolean
  onError?: (error: Error) => void
}

export function useFlashcardMetrics(
  cardId: string,
  options: UseFlashcardMetricsOptions = {}
) {
  const { enabled = true, onError } = options
  const metricsRef = useRef<ImplicitMetrics>({
    viewStartTime: Date.now(),
    viewEndTime: null,
    flipCount: 0,
    scrollDepth: 0,
    editAttempted: false,
    copyAttempted: false,
  })
  const sentRef = useRef(false)

  const sendMetrics = useCallback(
    async (skipped: boolean = false) => {
      if (sentRef.current || !enabled) return
      sentRef.current = true

      const metrics = metricsRef.current
      const viewTimeMs = (metrics.viewEndTime || Date.now()) - metrics.viewStartTime

      try {
        await submitImplicitSignal({
          card_id: cardId,
          view_time_ms: viewTimeMs,
          flip_count: metrics.flipCount,
          scroll_depth: metrics.scrollDepth,
          edit_attempted: metrics.editAttempted,
          copy_attempted: metrics.copyAttempted,
          skipped,
        })
      } catch (error) {
        onError?.(error as Error)
      }
    },
    [cardId, enabled, onError]
  )

  useEffect(() => {
    if (!enabled) return

    const currentMetrics = metricsRef.current
    currentMetrics.viewStartTime = Date.now()
    sentRef.current = false

    const handleScroll = () => {
      const depth = window.scrollY / (document.body.scrollHeight - window.innerHeight)
      currentMetrics.scrollDepth = Math.max(currentMetrics.scrollDepth, Math.min(depth, 1))
    }

    const handleCopy = () => {
      currentMetrics.copyAttempted = true
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        currentMetrics.editAttempted = true
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    document.addEventListener('copy', handleCopy)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      currentMetrics.viewEndTime = Date.now()
      sendMetrics(false)

      window.removeEventListener('scroll', handleScroll)
      document.removeEventListener('copy', handleCopy)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [cardId, enabled, sendMetrics])

  const trackFlip = useCallback(() => {
    metricsRef.current.flipCount++
  }, [])

  const trackEditAttempt = useCallback(() => {
    metricsRef.current.editAttempted = true
  }, [])

  const trackSkip = useCallback(() => {
    metricsRef.current.viewEndTime = Date.now()
    sendMetrics(true)
  }, [sendMetrics])

  return {
    trackFlip,
    trackEditAttempt,
    trackSkip,
  }
}
