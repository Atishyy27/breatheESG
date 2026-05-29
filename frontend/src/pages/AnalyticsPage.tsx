import { useDashboardTrends } from '@/hooks/useDashboardTrends'
import { useReviewQueue } from '@/hooks/useReviewQueue'
import { SkeletonLoader } from '@/components/shared/SkeletonLoader'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart, Bar, Cell, AreaChart, Area,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ComposedChart,
} from 'recharts'

const SCOPE_COLORS = { SCOPE_1: '#3b82f6', SCOPE_2: '#22c55e', SCOPE_3: '#f59e0b' }
const GRID = 'hsl(var(--border))'
const TEXT = 'hsl(var(--muted-foreground))'

export function AnalyticsPage() {
  const { data: trends, isLoading } = useDashboardTrends()
  const { data: queue } = useReviewQueue()

  if (isLoading) return <SkeletonLoader variant="dashboard" />

  // ── Source type approval analytics ────────────────────────────
  const sourceStats = (queue || []).reduce<Record<string, { pending: number; suspicious: number; approved: number }>>(
    (acc, row) => {
      const src = row.source_type || 'Unknown'
      if (!acc[src]) acc[src] = { pending: 0, suspicious: 0, approved: 0 }
      if (row.review_status === 'PENDING') acc[src].pending++
      else if (row.review_status === 'SUSPICIOUS') acc[src].suspicious++
      else if (row.review_status === 'APPROVED') acc[src].approved++
      return acc
    }, {}
  )
  const sourceChartData = Object.entries(sourceStats).map(([name, v]) => ({ name, ...v }))

  // ── Approval rate (pie equiv) ──────────────────────────────────
  const totalQ = (queue || []).length
  const approvedQ = (queue || []).filter(r => r.review_status === 'APPROVED').length
  const suspiciousQ = (queue || []).filter(r => r.review_status === 'SUSPICIOUS').length
  const pendingQ = totalQ - approvedQ - suspiciousQ

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Temporal analysis, scope trends, and workflow performance
        </p>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Records', value: totalQ, color: 'text-blue-500' },
          { label: 'Approved', value: approvedQ, color: 'text-emerald-500' },
          { label: 'Suspicious', value: suspiciousQ, color: 'text-amber-500' },
          { label: 'Pending', value: pendingQ, color: 'text-muted-foreground' },
        ].map(s => (
          <div key={s.label} className="border border-border bg-card rounded-xl p-4">
            <div className="text-xs text-muted-foreground">{s.label}</div>
            <div className={`text-2xl font-bold tabular-nums mt-1 ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Stacked area: monthly Scope 1/2/3 breakdown */}
      {trends?.monthly && trends.monthly.length > 0 && (
        <div className="border border-border bg-card rounded-xl p-5">
          <h3 className="text-sm font-bold mb-1">Cumulative Scope Breakdown — Monthly</h3>
          <p className="text-xs text-muted-foreground mb-4">Stacked area by GHG Protocol scope classification</p>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trends.monthly}>
              <defs>
                {Object.entries(SCOPE_COLORS).map(([k, c]) => (
                  <linearGradient key={k} id={`fill-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={c} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={c} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} strokeOpacity={0.4} />
              <XAxis dataKey="period" tick={{ fontSize: 10, fill: TEXT }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 10, fill: TEXT }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                width={44}
              />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {Object.entries(SCOPE_COLORS).map(([k, c]) => (
                <Area
                  key={k}
                  type="monotone"
                  dataKey={k}
                  stackId="1"
                  stroke={c}
                  fill={`url(#fill-${k})`}
                  strokeWidth={1.5}
                  name={k.replace('_', ' ')}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* FY Comparison */}
      {trends?.fy_comparison && trends.fy_comparison.length >= 2 && (
        <div className="border border-border bg-card rounded-xl p-5">
          <h3 className="text-sm font-bold mb-1">Year-over-Year Comparison</h3>
          <p className="text-xs text-muted-foreground mb-4">CO₂e per scope by fiscal year</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={trends.fy_comparison}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} strokeOpacity={0.4} />
              <XAxis dataKey="fy" tick={{ fontSize: 11, fill: TEXT }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 10, fill: TEXT }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                width={44}
              />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {Object.entries(SCOPE_COLORS).map(([k, c]) => (
                <Bar key={k} dataKey={k} name={k.replace('_', ' ')} fill={c} radius={[4, 4, 0, 0]} maxBarSize={36} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Source-type review breakdown */}
      {sourceChartData.length > 0 && (
        <div className="border border-border bg-card rounded-xl p-5">
          <h3 className="text-sm font-bold mb-1">Review Pipeline by Source Type</h3>
          <p className="text-xs text-muted-foreground mb-4">Pending / Suspicious / Approved records per ingestion source</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sourceChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} strokeOpacity={0.4} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: TEXT }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: TEXT }} tickLine={false} axisLine={false} width={30} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="pending" fill="#6366f1" name="Pending" radius={[4, 4, 0, 0]} maxBarSize={28} />
              <Bar dataKey="suspicious" fill="#f59e0b" name="Suspicious" radius={[4, 4, 0, 0]} maxBarSize={28} />
              <Bar dataKey="approved" fill="#22c55e" name="Approved" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Activity breakdown */}
      {trends?.activity_breakdown && trends.activity_breakdown.length > 0 && (
        <div className="border border-border bg-card rounded-xl p-5">
          <h3 className="text-sm font-bold mb-1">Emissions by Activity Type</h3>
          <p className="text-xs text-muted-foreground mb-4">Total CO₂e per normalized activity classification</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={trends.activity_breakdown.map(r => ({
                name: r.activity_type.replace(/_/g, ' '),
                co2e: Math.round(r.total),
                records: r.count,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} strokeOpacity={0.4} />
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: TEXT }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 10, fill: TEXT }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                width={44}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const d = payload[0].payload
                  return (
                    <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-xl">
                      <p className="font-semibold capitalize">{d.name}</p>
                      <p className="font-mono">{d.co2e.toLocaleString()} kg CO₂e</p>
                      <p className="text-muted-foreground">{d.records} records</p>
                    </div>
                  )
                }}
              />
              <Bar dataKey="co2e" radius={[4, 4, 0, 0]}>
                {trends.activity_breakdown.map((_, i) => (
                  <Cell
                    key={i}
                    fill={Object.values(SCOPE_COLORS)[i % 3]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}