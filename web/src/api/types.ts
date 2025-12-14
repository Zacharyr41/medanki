export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Job {
  id: string
  status: JobStatus
  progress: number
  filename: string
  createdAt: string
  completedAt: string | null
  error: string | null
}

export type CardType = 'basic' | 'cloze' | 'vignette'

export interface Card {
  id: string
  front: string
  back: string
  clozeText: string | null
  tags: string[]
  type: CardType
}

export interface PreviewResponse {
  cards: Card[]
  totalCount: number
  jobId: string
}

export interface UploadOptions {
  exam?: string
  cardTypes?: string[]
  maxCardsPerChunk?: number
}

export class ApiError extends Error {
  public readonly status: number
  public readonly code: string | undefined

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}
