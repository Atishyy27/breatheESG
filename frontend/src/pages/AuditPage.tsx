import { useReviewQueue } from '@/hooks/useReviewQueue'
import { useDashboard } from '@/hooks/useDashboard'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FileSearch, CheckCircle2, Clock, AlertTriangle, Upload } from 'lucide-react'

export function AuditPage() {
  const { data: queue } = useReviewQueue()
  const { data: dashboard } = useDashboard()
  const { data: ledger = [] } = useQuery({
    queryKey: ['audit-ledger'],
    queryFn: () => apiClient.get('/audit/ledger/').then(r => r.data),
    refetchInterval: 15000,
  })

  const approvedRecords = ledger.slice(0, 100)
  const suspiciousRecords = (queue || []).filter(r => r.review_status === 'SUSPICIOUS')
  const allRecords = [...approvedRecords, ...(queue || [])].slice(0, 100)

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileSearch className="h-6 w-6 text-primary" />
          Audit Log
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Immutable record of all ingestion, normalization, and approval events
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Activities', value: allRecords.length, icon: <Upload className="h-4 w-4" />, color: 'text-blue-500' },
          { label: 'Approved & Locked', value: approvedRecords.length, icon: <CheckCircle2 className="h-4 w-4" />, color: 'text-emerald-500' },
          { label: 'Awaiting Review', value: (queue || []).filter(r => r.review_status === 'PENDING').length, icon: <Clock className="h-4 w-4" />, color: 'text-muted-foreground' },
          { label: 'Anomalies Flagged', value: suspiciousRecords.length, icon: <AlertTriangle className="h-4 w-4" />, color: 'text-amber-500' },
        ].map(s => (
          <div key={s.label} className="border border-border bg-card rounded-xl p-4">
            <div className={`flex items-center gap-2 text-xs font-semibold mb-2 ${s.color}`}>
              {s.icon} {s.label}
            </div>
            <div className="text-2xl font-bold tabular-nums">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Approved records ledger */}
      <div className="border border-border bg-card rounded-xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-sm">Approved Emissions Ledger</h2>
            <p className="text-xs text-muted-foreground">Locked records — immutable post-approval</p>
          </div>
          <span className="text-xs bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 px-2 py-1 rounded-full font-semibold">
            {approvedRecords.length} locked
          </span>
        </div>

        {approvedRecords.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground text-sm">
            No approved records yet. Approve records in the Verification Queue.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted/20 border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase tracking-wide">Period</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase tracking-wide">Activity</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase tracking-wide">Facility</th>
                  <th className="px-4 py-3 text-right font-semibold text-muted-foreground uppercase tracking-wide">CO₂e (kg)</th>
                  <th className="px-4 py-3 text-center font-semibold text-muted-foreground uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {approvedRecords.map(r => (
                  <tr key={r.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3 font-mono">{r.reporting_period}</td>
                    <td className="px-4 py-3 font-mono text-muted-foreground">{r.activity_type}</td>
                    <td className="px-4 py-3">{r.facility_code || 'UNMAPPED'}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold">
                      {Number(r.co2e_kg).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 rounded-full text-[10px] font-bold uppercase">
                        <CheckCircle2 className="h-3 w-3" /> Locked
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Suspicious records explanation */}
      {suspiciousRecords.length > 0 && (
        <div className="border border-amber-500/20 bg-amber-500/5 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-amber-500/20">
            <h2 className="font-semibold text-sm text-amber-800 dark:text-amber-300">
              Flagged Anomalies Requiring Investigation
            </h2>
            <p className="text-xs text-amber-700/80 dark:text-amber-400/80 mt-0.5">
              These records were automatically detected as suspicious by the pipeline anomaly engine
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-amber-500/5 border-b border-amber-500/20">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Period</th>
                  <th className="px-4 py-3 text-left font-semibold">Activity</th>
                  <th className="px-4 py-3 text-left font-semibold">Anomaly</th>
                  <th className="px-4 py-3 text-right font-semibold">CO₂e (kg)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-500/10">
                {suspiciousRecords.map(r => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 font-mono">{r.reporting_period}</td>
                    <td className="px-4 py-3 font-mono">{r.activity_type}</td>
                    <td className="px-4 py-3 text-amber-700 dark:text-amber-400">
                      {r.anomaly_code?.replace('_', ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold">
                      {Number(r.co2e_kg).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}