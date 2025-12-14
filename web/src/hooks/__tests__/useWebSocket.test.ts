import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  close() {
    this.readyState = 3
    this.onclose?.()
  }

  send(_data: string) {}
}

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('connects to /api/ws/{jobId}', async () => {
    renderHook(() => useWebSocket('job-123'))

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    expect(MockWebSocket.instances[0].url).toContain('/api/ws/job-123')
  })

  it('receives progress message', async () => {
    const { result } = renderHook(() => useWebSocket('job-123'))

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({ type: 'progress', progress: 50, stage: 'chunking' })
      })
    })

    expect(result.current.progress).toBe(50)
    expect(result.current.stage).toBe('chunking')
  })

  it('receives complete message', async () => {
    const { result } = renderHook(() => useWebSocket('job-123'))

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({ type: 'complete', progress: 100 })
      })
    })

    expect(result.current.status).toBe('complete')
    expect(result.current.progress).toBe(100)
  })

  it('receives error message', async () => {
    const { result } = renderHook(() => useWebSocket('job-123'))

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({ type: 'error', error: 'Processing failed' })
      })
    })

    expect(result.current.status).toBe('error')
    expect(result.current.error).toBe('Processing failed')
  })

  it('reconnects on disconnect', async () => {
    vi.useFakeTimers()
    renderHook(() => useWebSocket('job-123'))

    await vi.waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onclose?.()
    })

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    expect(MockWebSocket.instances.length).toBe(2)
    vi.useRealTimers()
  })

  it('closes on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket('job-123'))

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    const ws = MockWebSocket.instances[0]
    const closeSpy = vi.spyOn(ws, 'close')

    unmount()

    expect(closeSpy).toHaveBeenCalled()
  })
})
