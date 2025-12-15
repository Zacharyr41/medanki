import { useState, useEffect, useRef, useCallback } from 'react'
import { API_BASE_URL } from '../api/client'

export type Stage = 'ingesting' | 'chunking' | 'classifying' | 'generating' | 'exporting'
export type Status = 'connecting' | 'connected' | 'complete' | 'error' | 'disconnected'

interface ProgressMessage {
  type: 'progress'
  progress: number
  stage: Stage
}

interface CompleteMessage {
  type: 'complete'
  progress: number
}

interface ErrorMessage {
  type: 'error'
  error: string
}

type WebSocketMessage = ProgressMessage | CompleteMessage | ErrorMessage

interface WebSocketState {
  progress: number
  stage: Stage
  status: Status
  error: string | null
  fileName: string | null
}

export function useWebSocket(jobId: string): WebSocketState {
  const [state, setState] = useState<WebSocketState>({
    progress: 0,
    stage: 'ingesting',
    status: 'connecting',
    error: null,
    fileName: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const shouldReconnectRef = useRef(true)

  const connect = useCallback(() => {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws')
    const url = `${wsUrl}/api/ws/${jobId}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setState(prev => ({ ...prev, status: 'connected' }))
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage

        if (message.type === 'progress') {
          setState(prev => ({
            ...prev,
            progress: message.progress,
            stage: message.stage,
            status: 'connected',
          }))
        } else if (message.type === 'complete') {
          setState(prev => ({
            ...prev,
            progress: message.progress,
            status: 'complete',
          }))
          shouldReconnectRef.current = false
        } else if (message.type === 'error') {
          setState(prev => ({
            ...prev,
            status: 'error',
            error: message.error,
          }))
          shouldReconnectRef.current = false
        }
      } catch {
        console.error('Failed to parse WebSocket message')
      }
    }

    ws.onclose = () => {
      if (shouldReconnectRef.current) {
        setState(prev => ({ ...prev, status: 'disconnected' }))
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 1000)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [jobId])

  useEffect(() => {
    shouldReconnectRef.current = true
    connect()

    return () => {
      shouldReconnectRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  return state
}
