import { create } from 'zustand'

interface Settings {
  deckName: string
  noteType: string
}

interface AppState {
  currentJobId: string | null
  settings: Settings
  setCurrentJobId: (jobId: string | null) => void
  setSettings: (settings: Partial<Settings>) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentJobId: null,
  settings: {
    deckName: 'MedAnki',
    noteType: 'Basic',
  },
  setCurrentJobId: (jobId) => set({ currentJobId: jobId }),
  setSettings: (newSettings) =>
    set((state) => ({
      settings: { ...state.settings, ...newSettings },
    })),
}))
