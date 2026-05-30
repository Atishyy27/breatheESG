import { useState, useRef } from 'react';
import { useUploads } from '@/hooks/useUploads';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { FileUp, Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export function UploadsPage() {
  const { history, upload } = useUploads();
  const [sourceType, setSourceType] = useState('SAP');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDragRoute = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(e.type === "dragover" || e.type === "dragenter");
  };

  const onDropFile = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileUploadExecution = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    upload.mutate(
      { file: selectedFile, type: sourceType },
      {
        onSuccess: () => {
          setSelectedFile(null);
        },
      }
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Section Header */}
      <div className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <FileUp className="h-6 w-6 text-primary" />
          Data Operations
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Ingest structured or tabular flat-file corporate activity logs.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6 items-start">
        {/* Left Control Column: Configuration & Drop Zone */}
        <div className="bg-card border border-border rounded-xl p-5 h-max space-y-4 shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Inbound Stream Config</h2>
          
          <form onSubmit={handleFileUploadExecution} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-zinc-500">Pipeline Target Profile</label>
              <select 
                value={sourceType}
                onChange={e => setSourceType(e.target.value)}
                className="w-full text-sm p-2.5 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="SAP">SAP Material Movements Export</option>
                <option value="UTILITY_BILL">Utility Portal Summary Bills</option>
                <option value="UTILITY_METER">Smart Meter Telemetry Stream</option>
                <option value="TRAVEL">Concur Routine Expenses JSON</option>
              </select>
            </div>

            {/* Interactive Drag & Drop Area */}
            <div
              onDragEnter={onDragRoute}
              onDragOver={onDragRoute}
              onDragLeave={onDragRoute}
              onDrop={onDropFile}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px] ${
                dragActive ? 'border-blue-500 bg-blue-500/5' : 'border-border bg-muted/20 hover:bg-muted/40'
              }`}
            >
              <input 
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={e => e.target.files && setSelectedFile(e.target.files[0])}
              />
              <FileUp className={`h-8 w-8 mb-3 ${selectedFile ? 'text-primary' : 'text-muted-foreground'}`} />
              {selectedFile ? (
                <div className="text-xs text-foreground font-semibold px-2 truncate max-w-full">
                  {selectedFile.name}
                </div>
              ) : (
                <span className="text-xs text-muted-foreground leading-relaxed px-4">
                  Drag & drop source flat file asset here, or <span className="text-blue-500 font-medium">browse local paths</span>
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={upload.isPending || !selectedFile}
              className="w-full py-2.5 bg-primary text-primary-foreground text-sm font-semibold rounded-lg shadow disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
            >
              {upload.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running Lineage Parsing...
                </>
              ) : "Execute Ingestion Stream"}
            </button>
          </form>
        </div>

        {/* Right Control Column: Upload Audit History Logs Table */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Historical Operation Registers</h2>
          
          {history.isLoading ? (
            <SkeletonLoader variant="table" />
          ) : (
            <div className="overflow-x-auto border border-border rounded-lg">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted/30 border-b border-border text-left text-muted-foreground font-medium">
                    <th className="p-3">Ingested Time</th>
                    <th className="p-3">Target Asset File</th>
                    <th className="p-3">Stream Code</th>
                    <th className="p-3 text-center">Engine Status</th>
                    <th className="p-3 text-right">Extracted Track Metrics (Pass / Warn / Err)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(history.data || []).map((log: any) => (
                    <tr key={log.id} className="hover:bg-muted/20 transition-colors">
                      <td className="p-3 text-muted-foreground">
                        {new Date(log.uploaded_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="p-3 font-semibold text-foreground truncate max-w-[180px]">{log.filename}</td>
                      <td className="p-3 font-mono"><code>{log.source_type}</code></td>
                      <td className="p-3 text-center">
                        <div className="flex flex-col items-center gap-1">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${
                            log.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 
                            log.status === 'FAILED' ? 'bg-red-500/10 text-red-600 border-red-500/20' : 
                            'bg-blue-500/10 text-blue-600 border-blue-500/20'
                          }`}>
                            {log.status === 'COMPLETED' ? <CheckCircle2 className="h-3 w-3" /> : log.status === 'FAILED' ? <AlertCircle className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                            {log.status}
                          </span>
                          {log.status === 'FAILED' && log.processing_error && (
                            <span className="text-[9px] text-red-500 max-w-[160px] text-center leading-tight" title={log.processing_error}>
                              {log.processing_error.length > 80 ? log.processing_error.slice(0, 80) + '…' : log.processing_error}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-right text-muted-foreground tabular-nums">
                        <span className="text-emerald-600 font-medium">{log.normalized_rows}</span> / <span className="text-amber-500 font-medium">{log.suspicious_rows}</span> / <span className="text-red-600 font-medium">{log.error_rows}</span>
                      </td>
                    </tr>
                  ))}
                  {(!history.data || history.data.length === 0) && (
                    <tr>
                      <td colSpan={5} className="text-center py-12 text-muted-foreground font-medium">
                        No document packets recorded inside this processing frame registry.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}