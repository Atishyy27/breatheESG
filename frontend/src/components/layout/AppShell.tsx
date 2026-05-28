import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShieldCheck, FileUp, Sun, Moon } from 'lucide-react';

export function AppShell() {
  const location = useLocation();
  
  // Initialize dark mode from localStorage or default to light
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark');

  // Sync theme state with DOM and localStorage
  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const navItems = [
    { path: '/', label: 'Executive Dashboard', icon: LayoutDashboard },
    { path: '/review', label: 'Verification Queue', icon: ShieldCheck },
    { path: '/uploads', label: 'Data Operations', icon: FileUp },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground transition-colors duration-200">
      {/* Permanent High-Density Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col justify-between shrink-0">
        <div>
          <div className="h-16 flex items-center px-6 border-b border-border font-bold tracking-tight text-lg">
            BreatheESG
            <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
              Workbench
            </span>
          </div>
          
          <nav className="p-4 space-y-1.5">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || 
                              (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <Link 
                  key={item.path}
                  to={item.path} 
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    isActive 
                      ? 'bg-primary/10 text-primary font-semibold' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                >
                  <item.icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        
        {/* Footer: User profile & Theme Toggle */}
        <div className="p-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex flex-col">
            <span className="font-medium text-foreground">Active Session</span>
            <span className="truncate w-36">analyst@breatheesg.com</span>
          </div>
          <button 
            onClick={() => setIsDark(!isDark)}
            className="p-2 rounded-md border border-border hover:bg-muted text-foreground transition-colors"
            title="Toggle Theme"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </aside>

      {/* Main Document Frame - Renders the active page */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}