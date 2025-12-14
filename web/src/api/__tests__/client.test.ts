import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { uploadFile, getJob, getPreview, downloadDeck, ApiError } from '../client'

describe('API Client', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('uploadFile', () => {
    it('sends file as FormData', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jobId: 'job-123' }),
      })

      await uploadFile(file)

      expect(mockFetch).toHaveBeenCalledTimes(1)
      const [url, options] = mockFetch.mock.calls[0]
      expect(url).toContain('/upload')
      expect(options.method).toBe('POST')
      expect(options.body).toBeInstanceOf(FormData)
      const formData = options.body as FormData
      expect(formData.get('file')).toBe(file)
    })

    it('returns jobId on success', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jobId: 'job-456' }),
      })

      const result = await uploadFile(file)

      expect(result).toEqual({ jobId: 'job-456' })
    })

    it('includes upload options in FormData when provided', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jobId: 'job-789' }),
      })

      await uploadFile(file, { exam: 'MCAT', cardTypes: ['cloze'], maxCardsPerChunk: 3 })

      const formData = mockFetch.mock.calls[0][1].body as FormData
      expect(formData.get('exam')).toBe('MCAT')
      expect(formData.get('cardTypes')).toBe('cloze')
      expect(formData.get('maxCardsPerChunk')).toBe('3')
    })
  })

  describe('getJob', () => {
    it('fetches job status by id', async () => {
      const mockJob = {
        id: 'job-123',
        status: 'processing',
        progress: 50,
        filename: 'test.pdf',
        createdAt: '2024-01-01T00:00:00Z',
        completedAt: null,
        error: null,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockJob),
      })

      const result = await getJob('job-123')

      expect(mockFetch).toHaveBeenCalledTimes(1)
      const [url] = mockFetch.mock.calls[0]
      expect(url).toContain('/jobs/job-123')
      expect(result).toEqual(mockJob)
    })
  })

  describe('getPreview', () => {
    it('fetches preview cards', async () => {
      const mockPreview = {
        cards: [
          { id: 'card-1', front: 'Q1', back: 'A1', clozeText: null, tags: ['biology'], type: 'basic' },
        ],
        totalCount: 1,
        jobId: 'job-123',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPreview),
      })

      const result = await getPreview('job-123')

      expect(mockFetch).toHaveBeenCalledTimes(1)
      const [url] = mockFetch.mock.calls[0]
      expect(url).toContain('/jobs/job-123/preview')
      expect(result).toEqual(mockPreview)
    })

    it('includes pagination params when provided', async () => {
      const mockPreview = { cards: [], totalCount: 0, jobId: 'job-123' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPreview),
      })

      await getPreview('job-123', { page: 2, limit: 10 })

      const [url] = mockFetch.mock.calls[0]
      expect(url).toContain('page=2')
      expect(url).toContain('limit=10')
    })
  })

  describe('downloadDeck', () => {
    it('returns Blob on success', async () => {
      const mockBlob = new Blob(['deck content'], { type: 'application/octet-stream' })
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      })

      const result = await downloadDeck('job-123')

      expect(mockFetch).toHaveBeenCalledTimes(1)
      const [url] = mockFetch.mock.calls[0]
      expect(url).toContain('/jobs/job-123/download')
      expect(result).toBeInstanceOf(Blob)
    })
  })

  describe('error handling', () => {
    it('throws on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(getJob('job-123')).rejects.toThrow('Network error')
    })

    it('throws ApiError with message from API on error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'Job not found', code: 'JOB_NOT_FOUND' }),
      })

      try {
        await getJob('job-123')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError)
        expect((error as ApiError).message).toBe('Job not found')
        expect((error as ApiError).status).toBe(404)
        expect((error as ApiError).code).toBe('JOB_NOT_FOUND')
      }
    })
  })
})
