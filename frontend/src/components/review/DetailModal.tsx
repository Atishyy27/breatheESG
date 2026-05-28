import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useApprove } from '@/hooks/useApprove';
import { getFacilityName } from '@/lib/constants';
import { X, CheckCircle2, AlertTriangle, Database } from 'lucide-react';

export function DetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [notes, setNotes] = useState("");
  const [bypass, setBypass] = useState(false);
  const { mutate: approve, isPending } = useApprove();

  useEffect(() => {
    api.get(`/review/${id}/`).then(res => setData(res.data));
    
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Enter' && e.ctrlKey && data) {
        if (!data.validation_issues?.some((i: any) => i.severity === 'ERROR') || (bypass && notes)) {
          approve({ id, bypass_validation: bypass, review_notes: notes }, { onSuccess: onClose });
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [id, data, bypass, notes, approve, onClose]);

  if (!data) return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
    </div>
  );

  const hasErrors = data.validation_issues?.some((i: any) => i.severity === 'ERROR');

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-6xl max-h-[90vh] rounded-xl shadow-2xl flex flex-col overflow-hidden border border-border animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border bg-muted/10 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold">Forensic Lineage: Record #{data.id}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{data.reporting_period} • {getFacilityName(data.facility_code)}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-muted rounded-md transition-colors"><X className="h-5 w-5 text-muted-foreground" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Timeline Tracker */}
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/20 p-3 rounded-lg border border-border">
            <div className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="h-4 w-4"/> Staged</div><span className="mx-2">→</span>
            <div className="flex items-center gap-1 text-emerald-600"><Database className="h-4 w-4"/> Prorated</div><span className="mx-2">→</span>
            <div className={`flex items-center gap-1 ${data.review_status === 'SUSPICIOUS' ? 'text-amber-500' : 'text-emerald-600'}`}>
              <AlertTriangle className="h-4 w-4"/> {data.review_status === 'SUSPICIOUS' ? 'Flagged' : 'Passed Bounds'}
            </div><span className="mx-2">→</span>
            <div className="text-blue-500 border-b border-dashed border-blue-500 pb-0.5">Pending Signature</div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Raw JSON View */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-muted-foreground">Raw Source Input (Line: {data.raw_line_number})</h3>
              <div className="bg-zinc-950 rounded-lg p-4 border border-zinc-800 h-[300px] overflow-auto">
                <pre className="text-[11px] text-zinc-300 font-mono leading-relaxed">
                  {JSON.stringify(data.raw_record_data, null, 2)}
                </pre>
              </div>
            </div>

            {/* Normalized View */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-muted-foreground">Normalized Activity</h3>
              <div className="bg-muted/10 rounded-lg p-5 border border-border space-y-4 h-[300px] overflow-auto">
                <div className="grid grid-cols-[120px_1fr] gap-3 text-sm">
                  <span className="text-muted-foreground">Category:</span><span className="font-medium">{data.scope} • {data.activity_type}</span>
                  <span className="text-muted-foreground">Input Quantity:</span><span className="font-mono">{data.quantity} {data.unit}</span>
                  <span className="text-muted-foreground">Emission Factor:</span><span className="font-mono text-xs">{data.factor_value_used} ({data.emission_factor_source})</span>
                </div>
                <div className="pt-4 border-t border-border">
                  <span className="text-muted-foreground text-xs uppercase tracking-wider block mb-1">Computed Carbon Mass</span>
                  <span className="text-3xl font-bold text-primary tabular-nums">{Number(data.co2e_kg).toLocaleString(undefined, {maximumFractionDigits:2})} <span className="text-sm font-normal text-muted-foreground">kg CO₂e</span></span>
                </div>
                {hasErrors && (
                  <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-600 text-xs rounded-md">
                    <strong>Validation Exceptions:</strong>
                    <ul className="list-disc pl-4 mt-1">{data.validation_issues?.map((i: any, idx: number) => <li key={idx}>{i.message}</li>)}</ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="p-6 border-t border-border bg-muted/10 space-y-4">
          <div className="flex gap-4">
            <textarea 
              className="flex-1 text-sm p-3 rounded-lg border border-border bg-background outline-none focus:border-primary resize-none h-20"
              placeholder={hasErrors ? "Mandatory: Detail bypass justification..." : "Optional context notes..."}
              value={notes} onChange={(e) => setNotes(e.target.value)}
            />
            <div className="flex flex-col gap-2 justify-end w-48">
              {hasErrors && (
                <label className="flex items-center gap-2 text-[11px] text-red-600 font-semibold cursor-pointer select-none">
                  <input type="checkbox" className="rounded" checked={bypass} onChange={(e) => setBypass(e.target.checked)} />
                  Force Audit Override
                </label>
              )}
              <button 
                onClick={() => approve({ id, bypass_validation: bypass, review_notes: notes }, { onSuccess: onClose })}
                disabled={isPending || (hasErrors && (!bypass || !notes))}
                className="w-full py-2.5 bg-primary text-primary-foreground text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
              >
                {isPending ? "Locking..." : "Approve Record"}
              </button>
            </div>
          </div>
          <div className="text-[10px] text-muted-foreground text-right font-mono">Shortcuts: Ctrl+Enter (Approve), Esc (Close)</div>
        </div>
      </div>
    </div>
  );
}