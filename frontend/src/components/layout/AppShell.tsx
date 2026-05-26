import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { FileUp, ShieldCheck, Sun, Moon } from 'lucide-react'

export function AppShell() {
  const location = useLocation()
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark')

  useEffect(() => {
    const root = window.document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Permanent High-Density Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col justify-between">
        <div>
          <div className="h-16 flex items-center px-6 border-b border-border font-bold tracking-tight text-lg">
            BreatheESG Workbench
          </div>
          <nav className="p-4 space-y-1">
            <Link 
              to="/review" 
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                location.pathname === '/review' ? 'bg-muted text-primary' : 'text-muted-foreground hover:bg-muted/50'
              }`}
            >
              <ShieldCheck className="h-4 w-4" />
              Verification Queue
            </Link>
            <Link 
              to="/uploads" 
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                location.pathname === '/uploads' ? 'bg-muted text-primary' : 'text-muted-foreground hover:bg-muted/50'
              }`}
            >
              <FileUp className="h-4 w-4" />
              Data Operations
            </Link>
          </nav>
        </div>
        
        <div className="p-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
          <span>analyst@breatheesg.com</span>
          <button 
            onClick={() => setIsDark(!isDark)}
            className="p-1.5 rounded-md border border-border hover:bg-muted text-foreground"
          >
            {isDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>
        </div>
      </aside>

      {/* Main Document Frame */}
      <main className="flex-1 overflow-y-auto p-8 position-relative">
        <Outlet />
      </main>
    </div>
  )
}