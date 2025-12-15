import { describe, it, expect, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useAuthStore } from '../authStore'

const mockUser = {
  id: 'user123',
  email: 'test@gmail.com',
  name: 'Test User',
  picture_url: 'https://example.com/photo.jpg',
}

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    localStorage.clear()
  })

  describe('initial state', () => {
    it('should start unauthenticated', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBe(null)
      expect(result.current.token).toBe(null)
    })

    it('should have isLoading false initially', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('login', () => {
    it('should set user and token on login', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.login(mockUser, 'mock.jwt.token')
      })

      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.token).toBe('mock.jwt.token')
    })

    it('should persist token to localStorage', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.login(mockUser, 'mock.jwt.token')
      })

      expect(localStorage.getItem('medanki_auth_token')).toBe('mock.jwt.token')
    })
  })

  describe('logout', () => {
    it('should clear user and token on logout', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.login(mockUser, 'mock.jwt.token')
      })

      expect(result.current.isAuthenticated).toBe(true)

      act(() => {
        result.current.logout()
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBe(null)
      expect(result.current.token).toBe(null)
    })

    it('should remove token from localStorage', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.login(mockUser, 'mock.jwt.token')
        result.current.logout()
      })

      expect(localStorage.getItem('medanki_auth_token')).toBe(null)
    })
  })

  describe('setLoading', () => {
    it('should update loading state', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.isLoading).toBe(true)

      act(() => {
        result.current.setLoading(false)
      })

      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('hydration from localStorage', () => {
    it('should hydrate token from localStorage', () => {
      localStorage.setItem('medanki_auth_token', 'stored.jwt.token')

      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.hydrate()
      })

      expect(result.current.token).toBe('stored.jwt.token')
    })
  })
})
