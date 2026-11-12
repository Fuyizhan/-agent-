import { useCallback, useState } from 'react'
import { api } from '../api/client'

interface AuthState {
  token: string | null
  username: string | null
  role: string | null
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>(() => ({
    token: localStorage.getItem('access_token'),
    username: localStorage.getItem('username'),
    role: localStorage.getItem('user_role'),
  }))

  const login = useCallback(async (username: string, password: string) => {
    const response = await api.login({ username, password })
    const payload = JSON.parse(atob(response.access_token.split('.')[1]))
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user_role', payload.role || 'viewer')
    localStorage.setItem('username', username)
    setAuth({ token: response.access_token, username, role: payload.role || 'viewer' })
    return response
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('username')
    setAuth({ token: null, username: null, role: null })
  }, [])

  return { ...auth, login, logout }
}
