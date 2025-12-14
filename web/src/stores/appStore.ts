import { create } from 'zustand'

export interface Settings {
  exam: string
  cardTypes: string[]
  maxCardsPerChunk: number
}

const DEFAULT_SETTINGS: Settings = {
  exam: 'MCAT',
  cardTypes: ['cloze', 'basic'],
  maxCardsPerChunk: 5,
}

interface AppState {
  currentJobId: string | null
  settings: Settings
  setCurrentJob: (jobId: string | null) => void
  setSettings: (settings: Partial<Settings>) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  currentJobId: null,
  settings: { ...DEFAULT_SETTINGS },
  setCurrentJob: (jobId) => set({ currentJobId: jobId }),
  setSettings: (newSettings) =>
    set((state) => ({
      settings: { ...state.settings, ...newSettings },
    })),
  reset: () =>
    set({
      currentJobId: null,
      settings: { ...DEFAULT_SETTINGS },
    }),
}))
