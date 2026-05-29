import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, FileUp, Sun, Moon,
  TrendingUp, FileSearch, Database, LogOut,
} from 'lucide-react';
import { useRole } from '@/context/RoleContext';

export function AppShell() {
  const location = useLocation();
  const { roleInfo, clearRole } = useRole();
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') === 'dark');

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
    { path: '/analytics', label: 'Analytics', icon: TrendingUp },
    { path: '/review', label: 'Verification Queue', icon: ShieldCheck },
    { path: '/uploads', label: 'Data Operations', icon: FileUp },
    { path: '/audit', label: 'Audit Log', icon: FileSearch },
    { path: '/generate', label: 'Dataset Studio', icon: Database },
  ].filter(item => roleInfo.routes.includes(item.path));

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground transition-colors duration-200">
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
              const isActive =
                location.pathname === item.path ||
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
                  <item.icon
                    className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-muted-foreground'}`}
                  />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="p-4 border-t border-border space-y-3">
          {/* Role indicator */}
          <div className="flex items-center gap-2 px-2 py-2 bg-muted/30 rounded-lg">
            <span className="text-xl">{roleInfo.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-foreground truncate">{roleInfo.label}</div>
              <div className="text-[10px] text-muted-foreground">Active session</div>
            </div>
            <button
              onClick={() => {
                clearRole();
                window.location.href = '/';
              }}
              className="p-1.5 hover:bg-muted rounded-md transition-colors text-muted-foreground hover:text-foreground"
              title="Switch role"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Theme toggle */}
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span className="truncate">analyst@breatheesg.com</span>
            <button
              onClick={() => setIsDark(!isDark)}
              className="p-1.5 rounded-md border border-border hover:bg-muted"
            >
              {isDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8 relative">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}