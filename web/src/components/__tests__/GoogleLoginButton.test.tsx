import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { GoogleLoginButton } from '../GoogleLoginButton'
import { useAuthStore } from '../../stores/authStore'

vi.mock('@react-oauth/google', () => ({
  GoogleLogin: ({ onSuccess }: { onSuccess: (response: { credential: string }) => void }) => (
    <button
      data-testid="google-login-button"
      onClick={() => onSuccess({ credential: 'mock-google-token' })}
    >
      Sign in with Google
    </button>
  ),
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('../../api/auth', () => ({
  loginWithGoogle: vi.fn().mockResolvedValue({
    access_token: 'mock-jwt-token',
    user: {
      id: 'user123',
      email: 'test@gmail.com',
      name: 'Test User',
      picture_url: 'https://example.com/photo.jpg',
    },
  }),
}))

describe('GoogleLoginButton', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    vi.clearAllMocks()
  })

  it('renders login button when unauthenticated', () => {
    render(<GoogleLoginButton />)
    expect(screen.getByTestId('google-login-button')).toBeInTheDocument()
  })

  it('renders user menu when authenticated', () => {
    useAuthStore.getState().login(
      {
        id: 'user123',
        email: 'test@gmail.com',
        name: 'Test User',
        picture_url: 'https://example.com/photo.jpg',
      },
      'mock-token'
    )

    render(<GoogleLoginButton />)
    expect(screen.getByTestId('user-menu')).toBeInTheDocument()
    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('calls login on successful Google auth', async () => {
    const { loginWithGoogle } = await import('../../api/auth')

    render(<GoogleLoginButton />)

    fireEvent.click(screen.getByTestId('google-login-button'))

    await waitFor(() => {
      expect(loginWithGoogle).toHaveBeenCalledWith('mock-google-token')
    })
  })

  it('shows logout option in user menu', () => {
    useAuthStore.getState().login(
      {
        id: 'user123',
        email: 'test@gmail.com',
        name: 'Test User',
        picture_url: null,
      },
      'mock-token'
    )

    render(<GoogleLoginButton />)

    const userMenu = screen.getByTestId('user-menu')
    fireEvent.click(userMenu)

    expect(screen.getByTestId('logout-button')).toBeInTheDocument()
  })
})
