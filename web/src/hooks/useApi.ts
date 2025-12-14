import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  uploadFile,
  getJob,
  getJobs,
  getPreview,
  downloadDeck,
  cancelJob,
} from '../api/client'
import type { UploadOptions } from '../api/types'

export function useUploadMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, options }: { file: File; options?: UploadOptions }) =>
      uploadFile(file, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useJobQuery(id: string | null) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => getJob(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const job = query.state.data
      if (job?.status === 'completed' || job?.status === 'failed') {
        return false
      }
      return 2000 // Poll every 2 seconds while processing
    },
  })
}

export function useJobsQuery() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
  })
}

export function usePreviewQuery(
  id: string | null,
  params?: { page?: number; limit?: number }
) {
  return useQuery({
    queryKey: ['preview', id, params],
    queryFn: () => getPreview(id!, params),
    enabled: !!id,
  })
}

export function useDownloadMutation() {
  return useMutation({
    mutationFn: (id: string) => downloadDeck(id),
  })
}

export function useCancelJobMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => cancelJob(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
