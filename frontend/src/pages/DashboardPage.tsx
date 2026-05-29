import { useDashboard } from '@/hooks/useDashboard'
import { useDashboardTrends } from '@/hooks/useDashboardTrends'
import { SkeletonLoader } from '@/components/shared/SkeletonLoader'
import { FACILITY_NAMES } from '@/lib/constants'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
  BarChart, Bar, AreaChart, Area,
} from 'recharts'
import {
  BarChart3, ShieldCheck, Activity, Factory,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react'

// ── Colour tokens (consistent across all charts) ─────────────────
const SCOPE_COLORS = {
  SCOPE_1: '#3b82f6',
  SCOPE_2: '#22c55e',
  SCOPE_3: '#f59e0b',
}
const CHART_BG = 'transparent'
const GRID_COLOR = 'hsl(var(--border))'
const TEXT_COLOR = 'hsl(var(--muted-foreground))'

// ── Recharts custom tooltip shell ────────────────────────────────
function ChartTooltip({
  active, payload, label, unit = 'kg',
}: {
  active?: boolean
  payload?: any[]
  label?: string
  unit?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-xl text-xs">
      <p className="font-semibold mb-2 text-foreground">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-mono font-semibold text-foreground">
            {Number(p.value).toLocaleString()} {unit}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Scope label map ────────────────────────────────────────────────
const SCOPE_LABELS: Record<string, string> = {
  SCOPE_1: 'Scope 1',
  SCOPE_2: 'Scope 2',
  SCOPE_3: 'Scope 3',
}

const ANOMALY_LABELS: Record<string, string> = {
  QUANTITY_SPIKE: 'Quantity Spike',
  NEGATIVE_VALUE: 'Negative Value',
  MISSING_FACILITY: 'Missing Facility',
  FUTURE_DATE: 'Future Date',
}

// ── Main page ──────────────────────────────────────────────────────
export function DashboardPage() {
  const { data, isLoading, isError } = useDashboard()
  const { data: trends, isLoading: trendsLoading } = useDashboardTrends()

  if (isLoading) return <SkeletonLoader variant="dashboard" />
  if (isError || !data) {
    return (
      <div className="p-6 border border-destructive/30 bg-destructive/10 text-destructive rounded-xl">
        <p className="font-bold">Telemetry Disconnected</p>
        <p className="text-sm mt-1">Backend API unreachable. Confirm Django server is running.</p>
      </div>
    )
  }

  // Prepare scope donut data
  const donutData = [
    { name: 'Scope 1', value: data.scope_1, color: SCOPE_COLORS.SCOPE_1 },
    { name: 'Scope 2', value: data.scope_2, color: SCOPE_COLORS.SCOPE_2 },
    { name: 'Scope 3', value: data.scope_3, color: SCOPE_COLORS.SCOPE_3 },
  ].filter(d => d.value > 0)

  // MoM change from trends API (replaces hardcoded 8.2%)
  const momChange = trends?.mom_change ?? null

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Executive Carbon Command Center
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          GHG Protocol corporate emissions — ingestion health and scope analytics
        </p>
      </div>

      {/* ── KPI Row ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Aggregate Carbon Load"
          icon={<BarChart3 className="h-4 w-4 text-blue-500" />}
          value={`${Math.round(data.total_co2e).toLocaleString()}`}
          unit="kg CO₂e"
          change={momChange}
          sub="approved activities"
        />
        <KPICard
          title="Verification Queue Status"
          icon={<ShieldCheck className={`h-4 w-4 ${data.suspicious_count > 0 ? 'text-amber-500' : 'text-emerald-500'}`} />}
          value={String(data.pending_count)}
          unit="pending"
          variant={data.suspicious_count > 0 ? 'warning' : 'default'}
          sub={`${data.suspicious_count} flagged anomalies`}
        />
        <KPICard
          title="Pipeline Success Rate"
          icon={<Activity className="h-4 w-4 text-emerald-500" />}
          value={`${data.success_rate.toFixed(1)}%`}
          unit=""
          sub={`${data.total_uploads} uploads this month`}
          variant="success"
        />
      </div>

      {/* ── Trend Chart + Donut ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Monthly Emissions Trend — takes 2/3 */}
        <div className="lg:col-span-2 border border-border bg-card rounded-xl p-5 shadow-sm">
          <SectionHeader
            title="Monthly Emissions Trend"
            sub="Scope-level CO₂e by reporting period"
          />
          {trendsLoading || !trends?.monthly?.length ? (
            <ChartPlaceholder message="No time-series data yet. Ingest more records." />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trends.monthly} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <defs>
                  {Object.entries(SCOPE_COLORS).map(([key, color]) => (
                    <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={color} stopOpacity={0.0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} strokeOpacity={0.5} />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 10, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={v => v.slice(5)}   // show MM only
                />
                <YAxis
                  tick={{ fontSize: 10, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                  width={40}
                />
                <Tooltip content={<ChartTooltip />} />
                <Legend
                  iconSize={8}
                  formatter={v => SCOPE_LABELS[v] ?? v}
                  wrapperStyle={{ fontSize: 11 }}
                />
                {Object.entries(SCOPE_COLORS).map(([key, color]) => (
                  <Area
                    key={key}
                    type="monotone"
                    dataKey={key}
                    name={key}
                    stroke={color}
                    strokeWidth={2}
                    fill={`url(#grad-${key})`}
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 0 }}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Scope Donut — takes 1/3 */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm flex flex-col">
          <SectionHeader
            title="GHG Scope Apportionment"
            sub="Approved activity distribution"
          />
          {donutData.length === 0 ? (
            <ChartPlaceholder message="Approve records to see scope distribution." />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={52}
                    outerRadius={78}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {donutData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} strokeWidth={0} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: any) => [`${Math.round(v).toLocaleString()} kg`, '']}
                    contentStyle={{
                      background: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      fontSize: 11,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Donut legend */}
              <div className="w-full space-y-1.5 mt-2">
                {donutData.map(d => {
                  const pct = data.total_co2e > 0
                    ? ((d.value / data.total_co2e) * 100).toFixed(1)
                    : '0.0'
                  return (
                    <div key={d.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: d.color }} />
                        <span className="text-foreground font-medium">{d.name}</span>
                      </div>
                      <span className="font-mono text-muted-foreground">{pct}%</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Facility Bar + FY Comparison ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Facility Horizontal Bar */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm">
          <SectionHeader
            title="Top Emitters Ranking"
            sub="CO₂e by facility (all records)"
          />
          {!data.top_facilities.length ? (
            <ChartPlaceholder message="No facility data available." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={data.top_facilities.map(f => ({
                  name: `${f.code}`,
                  co2e: Math.round(f.co2e),
                  label: FACILITY_NAMES[f.code] ?? f.name,
                }))}
                layout="vertical"
                margin={{ top: 0, right: 30, bottom: 0, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} strokeOpacity={0.5} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const d = payload[0].payload
                    return (
                      <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-xl">
                        <p className="font-semibold">{d.name}</p>
                        <p className="text-muted-foreground text-[10px]">{d.label}</p>
                        <p className="font-mono mt-1">{d.co2e.toLocaleString()} kg CO₂e</p>
                      </div>
                    )
                  }}
                />
                <Bar dataKey="co2e" name="CO₂e (kg)" radius={[0, 4, 4, 0]}>
                  {data.top_facilities.map((_, i) => (
                    <Cell
                      key={i}
                      fill={
                        i === 0 ? SCOPE_COLORS.SCOPE_1
                          : i === 1 ? SCOPE_COLORS.SCOPE_2
                          : SCOPE_COLORS.SCOPE_3
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* FY Comparison */}
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm">
          <SectionHeader
            title="Fiscal Year Comparison"
            sub="Scope emissions per calendar year"
          />
          {trendsLoading || !trends?.fy_comparison?.length ? (
            <ChartPlaceholder message="Insufficient data for FY comparison." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={trends.fy_comparison}
                margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} strokeOpacity={0.5} />
                <XAxis
                  dataKey="fy"
                  tick={{ fontSize: 11, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: TEXT_COLOR }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                  width={40}
                />
                <Tooltip content={<ChartTooltip unit="kg" />} />
                <Legend iconSize={8} formatter={v => SCOPE_LABELS[v] ?? v} wrapperStyle={{ fontSize: 11 }} />
                {Object.entries(SCOPE_COLORS).map(([key, color]) => (
                  <Bar key={key} dataKey={key} name={key} fill={color} radius={[4, 4, 0, 0]} maxBarSize={32} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Activity Breakdown + Anomaly Distribution ────────────── */}
      {trends && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Activity type breakdown */}
          <div className="border border-border bg-card rounded-xl p-5 shadow-sm">
            <SectionHeader
              title="Activity Type Distribution"
              sub="CO₂e by emission activity classification"
            />
            {!trends.activity_breakdown?.length ? (
              <ChartPlaceholder message="No activity data available." />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={trends.activity_breakdown.map(r => ({
                    name: r.activity_type.replace('_', ' ').replace('_', ' '),
                    value: Math.round(r.total),
                    count: r.count,
                  }))}
                  margin={{ top: 4, right: 4, bottom: 20, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} strokeOpacity={0.5} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 9, fill: TEXT_COLOR }}
                    tickLine={false}
                    axisLine={false}
                    angle={-20}
                    textAnchor="end"
                    height={40}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: TEXT_COLOR }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                    width={40}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-xl">
                          <p className="font-semibold capitalize">{d.name}</p>
                          <p className="font-mono">{d.value.toLocaleString()} kg CO₂e</p>
                          <p className="text-muted-foreground">{d.count} records</p>
                        </div>
                      )
                    }}
                  />
                  <Bar dataKey="value" fill={SCOPE_COLORS.SCOPE_2} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Anomaly distribution or pipeline */}
          <div className="border border-border bg-card rounded-xl p-5 shadow-sm">
            {trends.anomaly_distribution?.length > 0 ? (
              <>
                <SectionHeader
                  title="Anomaly Detection Results"
                  sub="Flagged record types from pipeline validation"
                />
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={trends.anomaly_distribution.map(r => ({
                      name: ANOMALY_LABELS[r.anomaly_code] ?? r.anomaly_code,
                      count: r.count,
                    }))}
                    margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} strokeOpacity={0.5} />
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: TEXT_COLOR }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: TEXT_COLOR }} tickLine={false} axisLine={false} width={30} />
                    <Tooltip formatter={(v: any) => [`${v} records`, 'Count']} />
                    <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <>
                <SectionHeader
                  title="Pipeline Health"
                  sub="Record count at each ingestion stage"
                />
                <PipelineFunnel pipeline={data.pipeline} />
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Facility Monthly Trend (if data exists) ─────────────── */}
      {trends?.facility_monthly && trends.facility_monthly.length > 1 && (
        <div className="border border-border bg-card rounded-xl p-5 shadow-sm">
          <SectionHeader
            title="Facility Emissions Timeline"
            sub={`Top ${trends.top_facility_codes.length} facilities — monthly CO₂e trend`}
          />
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trends.facility_monthly} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} strokeOpacity={0.5} />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 10, fill: TEXT_COLOR }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => String(v).slice(5)}
              />
              <YAxis
                tick={{ fontSize: 10, fill: TEXT_COLOR }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
                width={40}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {trends.top_facility_codes.map((code, i) => (
                <Line
                  key={code}
                  type="monotone"
                  dataKey={code}
                  name={`${code} (${FACILITY_NAMES[code] ?? 'Unknown'})`}
                  stroke={Object.values(SCOPE_COLORS)[i % 3]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 0 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────

function KPICard({
  title, icon, value, unit, sub, change, variant = 'default',
}: {
  title: string
  icon: React.ReactNode
  value: string
  unit: string
  sub?: string
  change?: number | null
  variant?: 'default' | 'warning' | 'success'
}) {
  const bg = {
    default: '',
    warning: 'bg-amber-500/5 border-amber-500/30',
    success: 'bg-emerald-500/5 border-emerald-500/30',
  }[variant]

  return (
    <div className={`border border-border ${bg} bg-card rounded-xl p-5 shadow-sm transition-shadow hover:shadow-md`}>
      <div className="flex justify-between items-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {title}
        {icon}
      </div>
      <div className="mt-3 flex items-end gap-2">
        <span className="text-3xl font-bold tabular-nums text-foreground">{value}</span>
        {unit && <span className="text-sm text-muted-foreground mb-1">{unit}</span>}
      </div>
      <div className="flex items-center gap-2 mt-1.5">
        {change !== null && change !== undefined && (
          <span className={`flex items-center gap-0.5 text-xs font-semibold ${
            change > 0 ? 'text-amber-500' : change < 0 ? 'text-emerald-500' : 'text-muted-foreground'
          }`}>
            {change > 0 ? <TrendingUp className="h-3 w-3" />
              : change < 0 ? <TrendingDown className="h-3 w-3" />
              : <Minus className="h-3 w-3" />}
            {Math.abs(change)}% MoM
          </span>
        )}
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
    </div>
  )
}

function SectionHeader({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-foreground">{title}</h3>
      <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>
    </div>
  )
}

function ChartPlaceholder({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-48 text-xs text-muted-foreground border border-dashed border-border rounded-lg">
      {message}
    </div>
  )
}

function PipelineFunnel({ pipeline }: { pipeline?: any }) {
  if (!pipeline) return <ChartPlaceholder message="No pipeline data." />
  const stages = [
    { label: 'Uploaded', value: pipeline.uploaded, color: '#6366f1' },
    { label: 'Parsed', value: pipeline.parsed, color: '#3b82f6' },
    { label: 'Normalized', value: pipeline.normalized, color: '#22c55e' },
    { label: 'Pending Review', value: pipeline.pending, color: '#f59e0b' },
    { label: 'Approved', value: pipeline.approved, color: '#10b981' },
  ]
  const max = Math.max(...stages.map(s => s.value), 1)
  return (
    <div className="space-y-2.5 mt-2">
      {stages.map(s => (
        <div key={s.label} className="flex items-center gap-3 text-xs">
          <span className="w-24 text-muted-foreground text-right shrink-0">{s.label}</span>
          <div className="flex-1 bg-muted rounded-full h-5 overflow-hidden">
            <div
              className="h-full rounded-full flex items-center justify-end pr-2 transition-all duration-700"
              style={{
                width: `${Math.max((s.value / max) * 100, 4)}%`,
                background: s.color,
              }}
            >
              <span className="text-white text-[10px] font-bold">{s.value}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}