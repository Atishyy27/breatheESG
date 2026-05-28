import { useDashboard } from '@/hooks/useDashboard';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { BarChart3, ShieldCheck, Activity, Factory } from 'lucide-react';

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();

  if (isLoading) return <SkeletonLoader variant="dashboard" />;
  if (isError || !data) {
    return (
      <div className="p-6 border border-red-200 bg-red-50 text-red-700 dark:bg-red-950/20 dark:border-red-900 rounded-xl">
        <h3 className="font-bold">Telemetry Disconnected</h3>
        <p className="text-sm mt-1">Failed to fetch dashboard metrics. Ensure the Django backend is running.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Executive Carbon Command Center</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          High-level sustainability metrics and data ingestion pipeline health.
        </p>
      </div>

      {/* KPI Cards Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Metric 1: Total Footprint */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Aggregate Carbon Load
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </div>
          <div className="text-3xl font-bold mt-3 tabular-nums text-foreground">
            {Math.round(data.total_co2e).toLocaleString()} <span className="text-sm font-normal text-muted-foreground">kg CO₂e</span>
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 font-medium flex items-center gap-1">
            ↑ 8.2% <span className="text-muted-foreground font-normal">vs previous period</span>
          </div>
        </div>

        {/* Metric 2: Queue Health */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Verification Queue Status
            <ShieldCheck className={`h-4 w-4 ${data.suspicious_count > 0 ? 'text-amber-500' : 'text-emerald-500'}`} />
          </div>
          <div className="text-3xl font-bold mt-3 tabular-nums text-foreground">
            {data.pending_count.toLocaleString()} <span className="text-sm font-normal text-muted-foreground">pending</span>
          </div>
          <div className={`text-xs mt-2 font-medium flex items-center gap-1 ${data.suspicious_count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground'}`}>
            {data.suspicious_count} flagged anomalies active
          </div>
        </div>

        {/* Metric 3: Pipeline Success */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex justify-between items-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Pipeline Success Rate
            <Activity className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-3xl font-bold mt-3 tabular-nums text-foreground">
            {data.success_rate.toFixed(1)}%
          </div>
          <div className="text-xs text-muted-foreground mt-2 font-medium flex items-center gap-1">
            {data.total_uploads.toLocaleString()} datasets parsed this month
          </div>
        </div>
      </div>

      {/* Lower Split: Scopes & Facilities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Scope Apportionment Bars */}
        <div className="border border-border bg-card rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-muted-foreground">
            <Activity className="h-4 w-4" /> GHG Protocol Scopes
          </div>
          
          <div className="space-y-5">
            <ScopeProgressRow label="Scope 1: Direct Mobile & Stationary" value={data.scope_1} total={data.total_co2e} bgClass="bg-blue-500 dark:bg-blue-600" />
            <ScopeProgressRow label="Scope 2: Purchased Utilities & Grid" value={data.scope_2} total={data.total_co2e} bgClass="bg-emerald-500 dark:bg-emerald-600" />
            <ScopeProgressRow label="Scope 3: Value Chain Procurement" value={data.scope_3} total={data.total_co2e} bgClass="bg-amber-500 dark:bg-amber-600" />
          </div>
        </div>

        {/* Top Facilities Table */}
        <div className="border border-border bg-card rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">
            <Factory className="h-4 w-4" /> Top Emitters Ranking
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="pb-3 font-medium">Facility Code</th>
                  <th className="pb-3 font-medium text-right">Computed Footprint</th>
                  <th className="pb-3 font-medium text-right">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.top_facilities.length === 0 ? (
                  <tr><td colSpan={3} className="py-4 text-center text-muted-foreground text-xs">No facility data mapped yet.</td></tr>
                ) : (
                  data.top_facilities.map((fac) => (
                    <tr key={fac.code} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3">
                        <div className="font-mono font-semibold text-foreground">{fac.code}</div>
                        <div className="text-xs text-muted-foreground truncate max-w-[200px]">{fac.name}</div>
                      </td>
                      <td className="py-3 text-right font-semibold tabular-nums text-foreground">
                        {Math.round(fac.co2e).toLocaleString()} <span className="text-xs font-normal text-muted-foreground">kg</span>
                      </td>
                      <td className="py-3 text-right font-medium tabular-nums text-blue-600 dark:text-blue-400">
                        {fac.percent.toFixed(1)}%
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// Internal component for the Scope progress bars
interface ScopeProps { label: string; value: number; total: number; bgClass: string; }
function ScopeProgressRow({ label, value, total, bgClass }: ScopeProps) {
  const percent = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
  return (
    <div className="space-y-1.5 text-sm">
      <div className="flex justify-between items-end">
        <span className="font-medium text-foreground">{label}</span>
        <span className="font-mono text-muted-foreground text-xs">
          <strong className="text-foreground">{Math.round(value).toLocaleString()} kg</strong> ({percent}%)
        </span>
      </div>
      <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
        <div className={`h-full ${bgClass} transition-all duration-1000 ease-out`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}