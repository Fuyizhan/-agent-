import { Activity } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/review')
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-1 p-4">
      <div className="w-full max-w-md bg-surface-2 border border-surface-3 rounded-2xl shadow-lg p-8">
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <div className="w-10 h-10 rounded-xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center">
            <Activity className="w-5 h-5 text-accent-cyan" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-text">合同审查系统</h1>
            <p className="text-xs text-muted font-mono">MULTI-AGENT REVIEW</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">用户名</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required
              className="w-full px-3 py-2.5 bg-surface-1 border border-surface-3 rounded-lg text-sm text-text focus:outline-none focus:border-accent-cyan" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">密码</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full px-3 py-2.5 bg-surface-1 border border-surface-3 rounded-lg text-sm text-text focus:outline-none focus:border-accent-cyan" />
          </div>
          {error && <p className="text-accent-red text-sm break-all">{error}</p>}
          <button disabled={loading} className="w-full bg-accent-cyan text-white py-2.5 rounded-lg text-sm font-medium disabled:opacity-50">
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <p className="mt-5 text-center text-xs text-muted">默认账号：admin / admin123</p>
      </div>
    </div>
  )
}
