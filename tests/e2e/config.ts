export const config = {
  baseUrl: process.env.E2E_BASE_URL || 'http://localhost:5173',
  apiUrl: process.env.E2E_API_URL || 'http://localhost:8000',
  isProduction: !!process.env.E2E_BASE_URL,
  timeout: process.env.E2E_BASE_URL ? 30000 : 10000,
}

export const EXAM_OPTIONS = ['MCAT', 'USMLE Step 1'] as const
export type ExamOption = (typeof EXAM_OPTIONS)[number]

export const CARD_TYPES = ['cloze', 'vignette'] as const
export type CardType = (typeof CARD_TYPES)[number]
