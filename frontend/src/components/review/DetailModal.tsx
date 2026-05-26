import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { useApprove } from '@/hooks/useApprove'
import { X, AlertTriangle, ShieldAlert, CheckCircle2 } from 'lucide-react'

interface DetailModalProps {
  activityId: number
  onClose: () => void
}

interface ValidationIssueData {
  severity: 'ERROR' | 'WARNING'
  issue_type: string
  message: string
}

interface DetailData {
  id: number
  scope: string
  scope_category: string
  activity_type: string
  activity_date: string
  reporting_period: string
  facility_code: string | null
  quantity: number | null
  unit: string
  factor_value_used: number
  emission_factor_source: string
  co2e_kg: number
  review_status: string
  anomaly_code: string | null
  anomaly_details: string | null
  raw_line_number: number
  raw_record_data: any
  validation_issues: ValidationIssueData[]
}

export function DetailModal({ activityId, onClose }: DetailModalProps) {
  const [data, setData] = useState<DetailData | null>(null)
  const [bypassValidation, setBypassValidation] = useState(false)
  const [reviewNotes, setReviewNotes] = useState("")
  const approveMutation = useApprove()

  useEffect(() => {
    api.get(`/review/${activityId}/`)
      .then(res => setData(res.data))
      .catch(err => console.error(err))
  }, [activityId])

  if (!data) {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-card p-6 rounded-lg border border-border flex items-center gap-3">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
          <span className="text-sm font-medium">Tracing Lineage Matrix...</span>
        </div>
      </div>
    )
  }

  const hasErrors = data.validation_issues.some(i => i.severity === 'ERROR')
  const isSubmitDisabled = hasErrors && (!bypassValidation || !reviewNotes.trim())

  const onConfirmApproval = async () => {
    try {
      await approveMutation.mutateAsync({
        id: data.id,
        bypass_validation: bypassValidation,
        review_notes: reviewNotes
      })
      onClose()
    } catch (err: any) {
      alert(err.response?.data?.error || "Approval transaction rejected.")
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl w-[1100px] max-w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
        {/* Header Block */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
          <div>
            <h2 className="text-base font-semibold tracking-tight">Audit Lineage: Record Context</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Lineage link matching raw textual data directly to normalized outputs.</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Inner Scrolling Terminal Panel */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Audit Trail Logic Progress Tracker Line */}
          <div className="flex items-center gap-4 text-xs font-medium text-muted-foreground border border-border p-3 rounded-lg bg-muted/10">
            <div className="flex items-center gap-1.5 text-primary"><CheckCircle2 className="h-3.5 w-3.5 text-green-600" /> Staged</div>
            <span>→</span>
            <div className="flex items-center gap-1.5 text-primary"><CheckCircle2 className="h-3.5 w-3.5 text-green-600" /> Prorated</div>
            <span>→</span>
            <div className={`flex items-center gap-1.5 ${data.review_status === 'SUSPICIOUS' ? 'text-amber-600' : 'text-primary'}`}>
              <AlertTriangle className="h-3.5 w-3.5" /> {data.review_status === 'SUSPICIOUS' ? 'Flagged Anomalous' : 'Cleared Limits'}
            </div>
            <span>→</span>
            <div className="border border-dashed border-border px-2 py-0.5 rounded">Awaiting Signature</div>
          </div>

          {/* Anomaly Alerts Header Banner */}
          {data.review_status === 'SUSPICIOUS' && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 flex gap-3 text-sm text-amber-800 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <div>
                <span className="font-semibold">Pipeline Anomaly Detected [{data.anomaly_code}]:</span>
                <p className="text-xs mt-0.5 text-amber-700/90 dark:text-amber-400/90">{data.anomaly_details}</p>
              </div>
            </div>
            )}

          {/* Core Visual Split Grid Display Block */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Side Terminal View: Immutable String Object Lineage */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">1. Raw Source Frame (Line: {data.raw_line_number})</h3>
              <pre className="text-xs font-mono p-4 rounded-lg bg-zinc-950 text-zinc-200 overflow-x-auto border border-zinc-800 leading-relaxed max-h-[320px]">
                {JSON.stringify(data.raw_record_data, null, 2)}
              </pre>
            </div>

            {/* Right Side Dashboard View: Target Normalized Parameters */}
            <div className="space-y-4 bg-muted/20 border border-border p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">2. Normalized Translation Matrix</h3>
                <div className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-3 text-sm leading-relaxed">
                  <span className="text-muted-foreground font-medium">Target Scope:</span>
                  <span className="font-semibold">{data.scope} &mdash; {data.scope_category}</span>
                  
                  <span className="text-muted-foreground font-medium">Namespace Context:</span>
                  <span><code>{data.activity_type}</code></span>

                  <span className="text-muted-foreground font-medium">Temporal Scale:</span>
                  <span>{data.activity_date} <span className="text-xs text-muted-foreground">(Period: {data.reporting_period})</span></span>

                  <span className="text-muted-foreground font-medium">Base Quantity:</span>
                  <span className="font-medium tabular-nums">{data.quantity?.toLocaleString() || '0.00'} {data.unit}</span>

                  <span className="text-muted-foreground font-medium">Derived Footprint:</span>
                  <span className="text-lg font-bold text-blue-600 dark:text-blue-400 tabular-nums">{data.co2e_kg.toFixed(2)} <span className="text-xs font-normal text-muted-foreground">kg CO₂e</span></span>

                  <span className="text-muted-foreground font-medium">Factor Provenance:</span>
                  <span className="text-xs text-muted-foreground">{data.factor_value_used} <em className="not-italic text-foreground">({data.emission_factor_source})</em></span>
                </div>
              </div>

              {/* Validation Issues Block */}
              {data.validation_issues.length > 0 && (
                <div className="border border-red-500/20 bg-red-500/5 p-3 rounded-md mt-4 text-xs text-red-800 dark:text-red-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold"><ShieldAlert className="h-3.5 w-3.5" /> Validation Exceptions Active:</div>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {data.validation_issues.map((issue, idx) => (
                      <li key={idx}><strong>[{issue.severity}]</strong> {issue.message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Lower Workflow Panel Logic Blocks */}
          <div className="border-t border-border pt-6 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-primary">3. Operational Sign-off Node</h3>
            
            {has_errors && (
              <label className="flex items-center gap-2 p-2 rounded border border-red-200 bg-red-500/5 text-xs font-semibold text-red-900 dark:text-red-400 dark:border-red-950 cursor-pointer w-max">
                <input 
                  type="checkbox" 
                  checked={bypassValidation} 
                  onChange={e => setBypassValidation(e.target.checked)} 
                  className="rounded border-border"
                />
                Override structural validation locks (Generates auditable bypass tag)
              </label>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Verification Ledger Summary Notes</label>
              <textarea
                rows={3}
                placeholder={has_errors ? "This field is mandatory. Provide explicit reasoning explaining validation override adjustments..." : "Enter verification remarks detailing background checks (Optional)..."}
                value={reviewNotes}
                onChange={e => setReviewNotes(e.target.value)}
                className="w-full text-sm font-sans p-2.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>
        </div>

        {/* Footer Configuration Array */}
        <div className="p-4 border-t border-border bg-muted/20 flex justify-end gap-2">
          <button 
            onClick={handleReject}
            className="px-4 py-2 text-xs font-semibold rounded-md border border-red-600/30 text-red-600 hover:bg-red-500/5 transition-colors"
          >
            Archive Context Row
          </button>
          <button
            onClick={onConfirmApproval}
            disabled={isSubmitDisabled || approveMutation.isPending}
            className="px-5 py-2 text-xs font-semibold text-primary-foreground bg-primary hover:bg-primary-hover rounded-md disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {approveMutation.isPending ? "Sealing Entry..." : "Verify & Approve Entry"}
          </button>
        </div>
      </div>
    </div>
  )
}