import { create } from 'zustand'
import type { Job } from '../api/types'

interface JobState {
  _jobsMap: Map<string, Job>
  jobs: Job[]
  addJob: (job: Job) => void
  updateJob: (id: string, partial: Partial<Job>) => void
  removeJob: (id: string) => void
  getJob: (id: string) => Job | undefined
  clearJobs: () => void
}

export const useJobStore = create<JobState>((set, get) => ({
  _jobsMap: new Map(),
  jobs: [],
  addJob: (job) =>
    set((state) => {
      const newMap = new Map(state._jobsMap)
      newMap.set(job.id, job)
      return { _jobsMap: newMap, jobs: Array.from(newMap.values()) }
    }),
  updateJob: (id, partial) =>
    set((state) => {
      const existingJob = state._jobsMap.get(id)
      if (!existingJob) {
        return state
      }
      const newMap = new Map(state._jobsMap)
      newMap.set(id, { ...existingJob, ...partial })
      return { _jobsMap: newMap, jobs: Array.from(newMap.values()) }
    }),
  removeJob: (id) =>
    set((state) => {
      const newMap = new Map(state._jobsMap)
      newMap.delete(id)
      return { _jobsMap: newMap, jobs: Array.from(newMap.values()) }
    }),
  getJob: (id) => get()._jobsMap.get(id),
  clearJobs: () => set({ _jobsMap: new Map(), jobs: [] }),
}))
