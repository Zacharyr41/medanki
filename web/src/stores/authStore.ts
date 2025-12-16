import { create } from 'zustand'

export interface User {
  id: string
  email: string
  name: string
  picture_url?: string | null
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (user: User, token: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  hydrate: () => void
}

const TOKEN_KEY = 'medanki_auth_token'

const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

const initialToken = getStoredToken()

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  token: initialToken,
  isAuthenticated: false,
  isLoading: false,

  login: (user: User, token: string) => {
    localStorage.setItem(TOKEN_KEY, token)
    set({
      user,
      token,
      isAuthenticated: true,
      isLoading: false,
    })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    })
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading })
  },

  hydrate: () => {
    const token = getStoredToken()
    if (token) {
      set({ token })
    }
  },
}))
