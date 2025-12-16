import { API_BASE_URL, ApiError } from './client'
import { useAuthStore, type User } from '../stores/authStore'

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface GoogleLoginRequest {
  token: string
}

function getAuthHeaders(): HeadersInit {
  const token = useAuthStore.getState().token
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

async function handleAuthResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    useAuthStore.getState().logout()
    throw new ApiError('Unauthorized', 401, 'unauthorized')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.detail || `Request failed with status ${response.status}`,
      response.status,
      data.code
    )
  }
  return response.json()
}

export async function loginWithGoogle(googleToken: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: googleToken }),
  })

  return handleAuthResponse<AuthResponse>(response)
}

export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: getAuthHeaders(),
  })

  return handleAuthResponse<User>(response)
}

export async function logout(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    console.error('Logout API call failed')
  }

  useAuthStore.getState().logout()
}
