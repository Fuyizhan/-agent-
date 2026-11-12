import type { DetailedReview, LoginRequest, TaskResponse, TokenResponse } from '../types'

const BASE = ''

function handleUnauthorized(): never {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_role')
  localStorage.removeItem('username')
  window.location.href = '/login'
  throw new Error('登录已过期，请重新登录')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const response = await fetch(`${BASE}${path}`, { ...options, headers })
  if (response.status === 401) handleUnauthorized()
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

async function upload<T>(path: string, form: FormData): Promise<T> {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (response.status === 401) handleUnauthorized()
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

export const api = {
  login: (body: LoginRequest) =>
    request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  uploadReview: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return upload<TaskResponse>('/api/v1/review/upload', form)
  },

  getReview: (id: string) => request<DetailedReview>(`/api/v1/review/${id}`),

  downloadReport: async (id: string) => {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`${BASE}/api/v1/review/${id}/report`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (response.status === 401) handleUnauthorized()
    if (!response.ok) throw new Error(await response.text())
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `review_${id}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  },
}
