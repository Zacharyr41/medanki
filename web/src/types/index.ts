export interface TopicInfo {
  id: string
  title: string | null
}

export interface CardPreview {
  id: string
  type: 'cloze' | 'vignette' | 'basic_qa'
  text: string
  tags: string[]
  topics: TopicInfo[]
  status: string
  source?: string
  front?: string
  answer?: string
  explanation?: string
  distinguishing_feature?: string
  document_position: number
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

export type ExamType = 'MCAT' | 'USMLE'

export interface TaxonomyCategory {
  id: string
  title: string
  keywords: string[]
}

export interface FoundationalConcept {
  id: string
  title: string
  keywords: string[]
  categories: TaxonomyCategory[]
}

export interface MCATTaxonomy {
  exam: 'MCAT'
  version: string
  foundational_concepts: FoundationalConcept[]
}

export interface USMLETopic {
  id: string
  title: string
  keywords: string[]
}

export interface USMLESystem {
  id: string
  title: string
  keywords: string[]
  topics: USMLETopic[]
}

export interface USMLETaxonomy {
  exam: 'USMLE'
  version: string
  systems: USMLESystem[]
}

export type Taxonomy = MCATTaxonomy | USMLETaxonomy

export interface TaxonomySearchResult {
  id: string
  title: string
  path: string[]
  type: 'foundational_concept' | 'content_category' | 'topic' | 'system'
}

export type FeedbackType = 'thumbs_up' | 'thumbs_down'

export type FeedbackCategory =
  | 'inaccurate'
  | 'unclear'
  | 'wrong_answer'
  | 'wrong_topic'
  | 'too_complex'
  | 'too_simple'
  | 'duplicate'

export interface FeedbackRequest {
  card_id: string
  feedback_type: FeedbackType
  categories?: FeedbackCategory[]
  comment?: string
  card_text?: string
  topic_id?: string
}

export interface CorrectionRequest {
  card_id: string
  original_topic_id: string
  corrected_topic_id: string
  confidence?: number
  comment?: string
}

export interface ImplicitSignalRequest {
  card_id: string
  view_time_ms: number
  flip_count: number
  scroll_depth: number
  edit_attempted: boolean
  copy_attempted: boolean
  skipped: boolean
}

export interface FeedbackResponse {
  id: string
  card_id: string
  user_id: string
  feedback_type: FeedbackType
  categories: FeedbackCategory[]
  comment: string | null
  created_at: string
}

export interface FeedbackAggregate {
  card_id: string
  total_thumbs_up: number
  total_thumbs_down: number
  approval_rate: number
  avg_view_time_ms: number
  correction_count: number
  most_common_categories: FeedbackCategory[]
  needs_review: boolean
}
