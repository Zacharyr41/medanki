import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { useAuthStore } from '../stores/authStore'
import { loginWithGoogle, logout as apiLogout } from '../api/auth'

export function GoogleLoginButton() {
  const { user, isAuthenticated, login, logout, setLoading } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGoogleSuccess = async (credentialResponse: { credential?: string }) => {
    if (!credentialResponse.credential) {
      setError('No credential received from Google')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await loginWithGoogle(credentialResponse.credential)
      login(response.user, response.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      console.error('Login error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      await apiLogout()
    } catch (err) {
      console.error('Logout error:', err)
    }
    logout()
    setMenuOpen(false)
  }

  if (isAuthenticated && user) {
    return (
      <div className="relative">
        <button
          data-testid="user-menu"
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100"
        >
          {user.picture_url ? (
            <img
              src={user.picture_url}
              alt={user.name}
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium">
              {user.name.charAt(0).toUpperCase()}
            </div>
          )}
          <span className="font-medium">{user.name}</span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border py-1 z-50">
            <div className="px-4 py-2 text-sm text-gray-500 border-b">
              {user.email}
            </div>
            <button
              data-testid="logout-button"
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={() => setError('Google login failed')}
      />
      {error && (
        <p className="text-red-500 text-sm mt-2">{error}</p>
      )}
    </div>
  )
}
