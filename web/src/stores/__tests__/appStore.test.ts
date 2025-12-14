import { describe, it, expect, beforeEach } from 'vitest'
import { useAppStore } from '../appStore'

describe('appStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAppStore.getState().reset()
  })

  describe('initial state', () => {
    it('has correct default values', () => {
      const state = useAppStore.getState()

      expect(state.currentJobId).toBeNull()
      expect(state.settings).toEqual({
        exam: 'MCAT',
        cardTypes: ['cloze', 'basic'],
        maxCardsPerChunk: 5,
      })
    })
  })

  describe('setCurrentJob', () => {
    it('sets currentJobId', () => {
      const { setCurrentJob } = useAppStore.getState()

      setCurrentJob('job-123')

      expect(useAppStore.getState().currentJobId).toBe('job-123')
    })

    it('can set currentJobId to null', () => {
      const { setCurrentJob } = useAppStore.getState()
      setCurrentJob('job-123')

      setCurrentJob(null)

      expect(useAppStore.getState().currentJobId).toBeNull()
    })
  })

  describe('setSettings', () => {
    it('updates settings partially', () => {
      const { setSettings } = useAppStore.getState()

      setSettings({ exam: 'USMLE' })

      const state = useAppStore.getState()
      expect(state.settings.exam).toBe('USMLE')
      expect(state.settings.cardTypes).toEqual(['cloze', 'basic'])
      expect(state.settings.maxCardsPerChunk).toBe(5)
    })

    it('updates multiple settings at once', () => {
      const { setSettings } = useAppStore.getState()

      setSettings({ exam: 'USMLE', maxCardsPerChunk: 3 })

      const state = useAppStore.getState()
      expect(state.settings.exam).toBe('USMLE')
      expect(state.settings.maxCardsPerChunk).toBe(3)
    })
  })

  describe('reset', () => {
    it('clears all state to defaults', () => {
      const { setCurrentJob, setSettings, reset } = useAppStore.getState()
      setCurrentJob('job-123')
      setSettings({ exam: 'USMLE', maxCardsPerChunk: 10 })

      reset()

      const state = useAppStore.getState()
      expect(state.currentJobId).toBeNull()
      expect(state.settings).toEqual({
        exam: 'MCAT',
        cardTypes: ['cloze', 'basic'],
        maxCardsPerChunk: 5,
      })
    })
  })
})
