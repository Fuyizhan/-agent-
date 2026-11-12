import { Activity, FileSearch, LogOut, Moon, Sun } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'

export default function Layout() {
  const { username, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-surface-1 text-text">
      <header className="h-16 border-b border-surface-3 bg-surface-2 flex items-center px-4 md:px-8 gap-4">
        <div className="flex items-center gap-2.5 mr-auto">
          <div className="w-9 h-9 rounded-lg bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center">
            <Activity className="w-4 h-4 text-accent-cyan" />
          </div>
          <div>
            <h1 className="text-sm font-semibold">合同审查</h1>
            <p className="text-[10px] text-muted font-mono">MULTI-AGENT</p>
          </div>
        </div>
        <NavLink
          to="/review"
          className={({ isActive }) => `flex items-center gap-2 text-sm px-3 py-2 rounded-lg ${isActive ? 'bg-accent-cyan/10 text-accent-cyan' : 'text-muted hover:text-text'}`}
        >
          <FileSearch className="w-4 h-4" />
          <span className="hidden sm:inline">新审查</span>
        </NavLink>
        <button onClick={toggle} className="p-2 text-muted hover:text-text" title="切换主题">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
        <span className="hidden md:inline text-xs text-muted">{username}</span>
        <button onClick={handleLogout} className="p-2 text-muted hover:text-text" title="退出登录">
          <LogOut className="w-4 h-4" />
        </button>
      </header>
      <main className="max-w-6xl mx-auto p-4 md:p-8">
        <Outlet />
      </main>
    </div>
  )
}
