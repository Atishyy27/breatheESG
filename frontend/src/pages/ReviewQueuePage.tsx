import { useState } from 'react';
import { useReviewQueue } from '@/hooks/useReviewQueue';
import { api } from '@/lib/api';
import { DetailModal } from '@/components/review/DetailModal';
import { AnomalyTooltip } from '@/components/review/AnomalyTooltip';
import { EmptyState } from '@/components/shared/EmptyState';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { getFacilityName } from '@/lib/constants';
import { ShieldCheck, Download, Search, Filter } from 'lucide-react';
import { toast } from 'sonner';

export function ReviewQueuePage() {
  const { data: queue, isLoading, refetch } = useReviewQueue();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [selected, setSelected] = useState<number[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);

  const filtered = (queue || []).filter((item: any) => {
    const s = search.toLowerCase();
    const matchSearch = (item.facility_code || "").toLowerCase().includes(s) || item.activity_type.toLowerCase().includes(s);
    const matchFilter = filter === "ALL" || item.review_status === filter;
    return matchSearch && matchFilter;
  });

  const handleBatch = async () => {
    if (!selected.length) return;
    if (!window.confirm(`Approve ${selected.length} selected activities for audit lock?`)) return;
    
    setIsBatchProcessing(true);
    try {
      await api.batchApprove(selected);
      toast.success(`Batch Processed: ${selected.length} records verified.`);
      setSelected([]);
      refetch();
    } catch (err: any) {
      toast.error('Batch Failed', { description: err.response?.data?.error || 'Validation errors exist in selection.' });
    } finally {
      setIsBatchProcessing(false);
    }
  };

  const handleExport = () => {
    window.open('/api/review/export/', '_blank');
  };

  if (isLoading) return <SkeletonLoader variant="table" />;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-primary" /> Analyst Verification Queue
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Audit, override, and lock normalized carbon assets.</p>
        </div>
        <div className="flex gap-3">
          {selected.length > 0 && (
            <button 
              onClick={handleBatch} 
              disabled={isBatchProcessing}
              className="px-4 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-lg shadow-sm hover:bg-primary/90 transition-opacity"
            >
              Approve Selected ({selected.length})
            </button>
          )}
          <button onClick={handleExport} className="flex items-center gap-2 px-4 py-2 bg-card border border-border text-sm font-semibold rounded-lg hover:bg-muted transition-colors">
            <Download className="h-4 w-4" /> Export Ledger
          </button>
        </div>
      </div>

      {/* Filters Control Subpanel */}
      <div className="flex gap-3 p-1 bg-card border border-border rounded-lg p-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search facilities or activities..." 
            value={search} 
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-background border border-border focus:ring-1 focus:ring-primary outline-none"
          />
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)} 
            className="px-4 py-2 text-sm rounded-lg bg-background border border-border outline-none text-foreground"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending Only</option>
            <option value="SUSPICIOUS">Anomalies Only</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      {filtered.length === 0 ? <EmptyState /> : (
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/30 border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
              <tr>
                <th className="p-4 w-12">
                  <input 
                    type="checkbox" 
                    className="rounded border-border" 
                    checked={selected.length === filtered.length && filtered.length > 0} 
                    onChange={() => setSelected(selected.length === filtered.length ? [] : filtered.map((i: any) => i.id))} 
                  />
                </th>
                <th className="p-4 font-semibold">Period</th>
                <th className="p-4 font-semibold">Facility</th>
                <th className="p-4 font-semibold">Activity Map</th>
                <th className="p-4 font-semibold text-right">Computed CO₂e</th>
                <th className="p-4 font-semibold">Status Vectors</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((row: any) => (
                <tr 
                  key={row.id} 
                  onClick={() => setActiveId(row.id)} 
                  className={`cursor-pointer transition-colors group ${
                    row.review_status === 'SUSPICIOUS' ? 'bg-amber-500/5 hover:bg-amber-500/10' : 'hover:bg-muted/30'
                  }`}
                >
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <input 
                      type="checkbox" 
                      className="rounded border-border" 
                      checked={selected.includes(row.id)} 
                      onChange={() => setSelected(prev => prev.includes(row.id) ? prev.filter(id => id !== row.id) : [...prev, row.id])} 
                    />
                  </td>
                  <td className="p-4 font-mono text-xs">{row.reporting_period}</td>
                  <td className="p-4">
                    <div className="font-semibold">{row.facility_code || 'UNMAPPED'}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-[200px]">{getFacilityName(row.facility_code)}</div>
                  </td>
                  <td className="p-4 text-xs font-mono text-muted-foreground">{row.activity_type}</td>
                  <td className="p-4 text-right font-mono font-bold tabular-nums">
                    {Number(row.co2e_kg).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} kg
                  </td>
                  <td className="p-4 flex gap-2 items-center">
                    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${
                      row.review_status === 'SUSPICIOUS' 
                        ? 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900' 
                        : 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900'
                    }`}>
                      {row.review_status}
                    </span>
                    <AnomalyTooltip code={row.anomaly_code || ''} details={row.anomaly_details} />
                    {row.inline_issues && row.inline_issues.length > 0 ? (
                      <span className="text-[10px] font-bold text-red-500 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                        {row.inline_issues.length} ERR
                      </span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeId && <DetailModal id={activeId} onClose={() => { setActiveId(null); refetch(); }} />}
    </div>
  );
}