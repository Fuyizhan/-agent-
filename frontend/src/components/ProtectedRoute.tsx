import { Navigate, Outlet } from 'react-router-dom'

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return Date.now() >= payload.exp * 1000
  } catch {
    return true
  }
}

export default function ProtectedRoute() {
  const token = localStorage.getItem('access_token')

  if (!token || isTokenExpired(token)) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('username')
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
