import { useState } from 'react'
import { useReviewQueue } from '@/hooks/useReviewQueue'
import { DetailModal } from '@/components/review/DetailModal'
import { api } from '@/lib/api'
import { ShieldCheck, Search, Filter, CheckCircle } from 'lucide-react'

export function ReviewQueuePage() {
  const { data: queue = [], refetch } = useReviewQueue()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PENDING" | "SUSPICIOUS">("ALL")
  const [selectedRows, setSelectedRows] = useState<number[]>([])
  const [activeDetailId, setActiveDetailId] = useState<number | null>(null)
  const [isBatchProcessing, setIsBatchProcessing] = useState(false)

  // Filter matrix evaluation matching Task 3 requirements
  const filteredQueue = queue.filter(item => {
    const matchesSearch = (item.facility_code || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (item.activity_type || "").toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === "ALL" || item.review_status === statusFilter
    return matchesSearch && matchesStatus
  })

  const toggleSelectAll = () => {
    if (selectedRows.length === filteredQueue.length) {
      setSelectedRows([])
    } else {
      setSelectedRows(filteredQueue.map(item => item.id))
    }
  }

  const toggleSelectRow = (id: number) => {
    setSelectedRows(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id])
  }

  const executeBatchApproval = async () => {
    if (!selectedRows.length) return
    if (!window.confirm(`Approve ${selectedRows.length} selected activities for audit lock?`)) return
    
    setIsBatchProcessing(true)
    try {
      const response = await api.post('/review/batch-approve/', { activity_ids: selectedRows })
      alert(response.data.message || "Batch successfully verified.")
      setSelectedRows([])
      refetch()
    } catch (err: any) {
      alert(err.response?.data?.error || "Batch approval halted due to active validation errors.")
    } finally {
      setIsBatchProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Upper Control Console Block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-zinc-500" />
            Analyst Verification Queue
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Review, override, or approve corporate carbon footprint records.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {selectedRows.length > 0 && (
            <button 
              onClick={executeBatchApproval}
              disabled={isBatchProcessing}
              className="flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary-hover px-3 py-1.5 rounded-md text-xs font-semibold shadow transition-colors"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              Approve Selected ({selectedRows.length})
            </button>
          )}
          <a href="/api/review/export/" target="_blank" rel="noreferrer">
            <button className="border border-border bg-card text-foreground hover:bg-muted px-3 py-1.5 rounded-md text-xs font-semibold transition-colors">
              Export Approved Ledger
            </button>
          </a>
        </div>
      </div>

      {/* Filter and Search Action Grid Panel */}
      <div className="flex flex-wrap items-center gap-3 bg-card p-3 rounded-lg border border-border">
        <div className="relative flex-1 min-w-[24px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Fuzzy filter by facility code or emissions source scope..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-md bg-background border border-border focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <select 
            value={statusFilter} 
            onChange={e => setStatusFilter(e.target.value as any)}
            className="bg-background border border-border rounded-md px-2 py-1.5 font-medium text-foreground focus:outline-none"
          >
            <option value="ALL">Show All Pipeline Items</option>
            <option value="PENDING">Pending Standard Boundaries</option>
            <option value="SUSPICIOUS">Flagged System Anomalies</option>
          </select>
        </div>
      </div>

      {/* Main High-Density Data Matrix Grid Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden shadow-sm">
        <table className="w-full">
          <thead>
            <tr className="bg-muted/30 border-b border-border text-xs">
              <th className="w-10 px-4 py-3">
                <input 
                  type="checkbox" 
                  checked={selectedRows.length === filteredQueue.length && filteredQueue.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded border-border"
                />
              </th>
              <th>Reporting Window</th>
              <th>Activity Namespace</th>
              <th>Facility Ref</th>
              <th>Footprint Assessment</th>
              <th>Lineage Metrics & Warning Streams</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-xs">
            {filteredQueue.map(item => (
              <tr 
                key={item.id}
                onClick={() => setActiveDetailId(item.id)}
                className={`transition-colors hover:bg-muted/40 cursor-pointer ${
                  item.review_status === 'SUSPICIOUS' ? 'bg-amber-500/5 hover:bg-amber-500/10' : ''
                }`}
              >
                <td className="px-4 py-2.5" onClick={e => e.stopPropagation()}>
                  <input 
                    type="checkbox"
                    checked={selectedRows.includes(item.id)}
                    onChange={() => toggleSelectRow(item.id)}
                    className="rounded border-border"
                  />
                </td>
                <td className="font-medium">{item.reporting_period}</td>
                <td><code>{item.activity_type}</code></td>
                <td>{item.facility_code || <span className="text-red-500 font-semibold">Unmapped</span>}</td>
                <td className="font-semibold tabular-nums">{item.co2e_kg.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} kgCO₂e</td>
                <td>
                  <div className="flex flex-wrap gap-2 items-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                      item.review_status === 'SUSPICIOUS' 
                        ? 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900' 
                        : 'bg-zinc-100 text-zinc-800 border-zinc-200 dark:bg-zinc-900 dark:text-zinc-400 dark:border-zinc-800'
                    }`}>
                      {item.review_status}
                    </span>
                    
                    {/* Anomaly and Inline Warning Stream Injection Block */}
                    {item.anomaly_code && (
                      <span className="text-amber-700 dark:text-amber-400 font-medium font-mono text-[11px]">
                        ⚠ {item.anomaly_code.toLowerCase().replace('_', ' ')}
                      </span>
                    )}
                    {item.inline_issues && item.inline_issues.map((issue, idx) => (
                      <span key={idx} className="text-red-600 dark:text-red-400 font-medium font-mono text-[11px]">
                        ✗ {issue}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {filteredQueue.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-12 text-muted-foreground font-medium">
                  🎉 Verification queue clear. No data packets require manual authorization.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Lineage Detail Expansion Side-by-Side Modal Overlay */}
      {activeDetailId && (
        <DetailModal 
          activityId={activeDetailId} 
          onClose={() => {
            setActiveDetailId(null)
            refetch()
          }} 
        />
      )}
    </div>
  )
}