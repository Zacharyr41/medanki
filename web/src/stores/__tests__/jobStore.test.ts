import { describe, it, expect, beforeEach } from 'vitest'
import { useJobStore } from '../jobStore'
import type { Job } from '../../api/types'

describe('jobStore', () => {
  const mockJob: Job = {
    id: 'job-123',
    status: 'pending',
    progress: 0,
    filename: 'test.pdf',
    createdAt: '2024-01-01T00:00:00Z',
    completedAt: null,
    error: null,
  }

  beforeEach(() => {
    // Reset store state before each test
    useJobStore.getState().clearJobs()
  })

  describe('addJob', () => {
    it('adds job to list', () => {
      const { addJob, getJob } = useJobStore.getState()

      addJob(mockJob)

      expect(getJob('job-123')).toEqual(mockJob)
    })

    it('can add multiple jobs', () => {
      const { addJob, getJob } = useJobStore.getState()
      const job2: Job = { ...mockJob, id: 'job-456', filename: 'other.pdf' }

      addJob(mockJob)
      addJob(job2)

      expect(getJob('job-123')).toEqual(mockJob)
      expect(getJob('job-456')).toEqual(job2)
    })
  })

  describe('updateJob', () => {
    it('updates existing job status', () => {
      const { addJob, updateJob, getJob } = useJobStore.getState()
      addJob(mockJob)

      updateJob('job-123', { status: 'processing' })

      expect(getJob('job-123')?.status).toBe('processing')
    })

    it('updates job progress', () => {
      const { addJob, updateJob, getJob } = useJobStore.getState()
      addJob(mockJob)

      updateJob('job-123', { progress: 75 })

      expect(getJob('job-123')?.progress).toBe(75)
    })

    it('updates multiple fields at once', () => {
      const { addJob, updateJob, getJob } = useJobStore.getState()
      addJob(mockJob)

      updateJob('job-123', { status: 'completed', progress: 100, completedAt: '2024-01-01T01:00:00Z' })

      const updatedJob = getJob('job-123')
      expect(updatedJob?.status).toBe('completed')
      expect(updatedJob?.progress).toBe(100)
      expect(updatedJob?.completedAt).toBe('2024-01-01T01:00:00Z')
    })

    it('does nothing if job does not exist', () => {
      const { updateJob, getJob } = useJobStore.getState()

      updateJob('nonexistent', { status: 'processing' })

      expect(getJob('nonexistent')).toBeUndefined()
    })
  })

  describe('getJob', () => {
    it('retrieves specific job by id', () => {
      const { addJob, getJob } = useJobStore.getState()
      addJob(mockJob)

      const result = getJob('job-123')

      expect(result).toEqual(mockJob)
    })

    it('returns undefined for nonexistent job', () => {
      const { getJob } = useJobStore.getState()

      const result = getJob('nonexistent')

      expect(result).toBeUndefined()
    })
  })

  describe('removeJob', () => {
    it('removes job from list', () => {
      const { addJob, removeJob, getJob } = useJobStore.getState()
      addJob(mockJob)

      removeJob('job-123')

      expect(getJob('job-123')).toBeUndefined()
    })

    it('does not affect other jobs', () => {
      const { addJob, removeJob, getJob } = useJobStore.getState()
      const job2: Job = { ...mockJob, id: 'job-456' }
      addJob(mockJob)
      addJob(job2)

      removeJob('job-123')

      expect(getJob('job-456')).toEqual(job2)
    })
  })

  describe('jobs getter', () => {
    it('returns all jobs as array', () => {
      const { addJob } = useJobStore.getState()
      const job2: Job = { ...mockJob, id: 'job-456' }
      addJob(mockJob)
      addJob(job2)

      const jobs = useJobStore.getState().jobs

      expect(jobs).toHaveLength(2)
      expect(jobs).toContainEqual(mockJob)
      expect(jobs).toContainEqual(job2)
    })
  })
})
