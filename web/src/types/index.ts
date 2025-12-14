export interface CardPreview {
  id: string
  type: 'cloze' | 'vignette' | 'basic_qa'
  text: string
  tags: string[]
  topics: string[]
  status: string
  source?: string
  front?: string
  answer?: string
  explanation?: string
  distinguishing_feature?: string
}

export interface PreviewResponse {
  cards: CardPreview[]
  total: number
  limit: number
  offset: number
}

export interface CardCounts {
  total: number
  cloze: number
  vignette: number
  basic_qa: number
}

export interface TimingInfo {
  created_at: string
  completed_at: string
  duration_seconds: number
}

export interface StatsResponse {
  counts: CardCounts
  topics: Record<string, number>
  timing: TimingInfo
}

export interface Job {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  document_id: string
  created_at: string
  updated_at: string
}
