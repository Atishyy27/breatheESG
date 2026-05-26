import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { FileUp, Database, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react'

interface UploadLog {
  id: number
  filename: string
  source_type: string
  status: string
  total_rows: number
  normalized_rows: number
  error_rows: number
  suspicious_rows: number
  uploaded_at: string
}

export function UploadsPage() {
  const [sourceType, setSourceType] = useState<'SAP' | 'UTILITY_BILL' | 'UTILITY_METER' | 'TRAVEL'>('SAP')
  const [file, setFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  // Custom internal queries tracking operational upload metrics
  const { data: uploads = [], refetch } = useQuery<UploadLog[]>({
    queryKey: ['upload-history'],
    queryFn: async () => {
      const response = await api.get('/uploads/')
      return response.data
    }
  })

  const onDragRoute = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(e.type === "dragover" || e.type === "dragenter")
  }

  const onDropFile = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const handleFileUploadExecution = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    
    setIsProcessing(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_type', sourceType)

    try {
      const response = await api.post('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const summary = response.data.upload_details
      alert(`Ingestion Successful!\nRecords Extracted: ${summary.total_records}\nNormalized: ${summary.successfully_normalized}\nErrors Blocked: ${summary.validation_errors_found}`)
      setFile(null)
      refetch()
    } catch (err: any) {
      alert(err.response?.data?.error || "Pipeline transformation execution halted.")
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <FileUp className="h-5 w-5 text-zinc-500" />
          Data Pipeline Operations
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">Ingest structured or tabular flat-file corporate activity logs.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6">
        {/* Left Control Column: The Ingestion Interactive Drop Frame */}
        <div className="bg-card border border-border rounded-xl p-5 h-max space-y-4 shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Inbound Stream Config</h2>
          
          <form onSubmit={handleFileUploadExecution} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-zinc-500">Pipeline Target Profile</label>
              <select 
                value={sourceType}
                onChange={e => setSourceType(e.target.value as any)}
                className="w-full text-xs p-2 rounded-md bg-background border border-border text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
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
              onClick={() => document.getElementById('file-picker-node')?.click()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[140px] ${
                dragActive ? 'border-blue-500 bg-blue-500/5' : 'border-border bg-muted/20 hover:bg-muted/40'
              }`}
            >
              <input 
                id="file-picker-node"
                type="file"
                className="hidden"
                onChange={e => e.target.files && setFile(e.target.files[0])}
              />
              <FileUp className="h-6 w-6 text-muted-foreground mb-2" />
              {file ? (
                <div className="text-xs text-foreground font-semibold px-2 truncate max-w-full">
                  {file.name}
                </div>
              ) : (
                <span className="text-xs text-muted-foreground leading-relaxed px-4">
                  Drag & drop source flat file asset here, or <span className="text-blue-500 font-medium">browse local paths</span>
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={isProcessing || !file}
              className="w-full py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-md shadow disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-hover transition-colors flex items-center justify-center gap-2"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Running Lineage Parsing...
                </>
              ) : "Execute Ingestion Stream"}
            </button>
          </form>
        </div>

        {/* Right Control Column: Upload Audit History Table Logs */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Historical Operation Registers</h2>
          
          <div className="overflow-x-auto border border-border rounded-lg">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/30 border-b border-border text-left">
                  <th className="p-3">Ingested Time</th>
                  <th className="p-3">Target Asset File</th>
                  <th className="p-3">Stream Code</th>
                  <th className="p-3">Engine Status</th>
                  <th className="p-3 text-right">Extracted Track Metrics</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {uploads.map(log => (
                  <tr key={log.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-3 text-muted-foreground">{log.uploaded_at}</td>
                    <td className="p-3 font-semibold text-foreground truncate max-w-[180px]">{log.filename}</td>
                    <td className="p-3"><code>{log.source_type}</code></td>
                    <td className="p-3">
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border uppercase ${
                        log.status === 'COMPLETED'
                          ? 'bg-green-500/5 text-green-700 border-green-500/20'
                          : 'bg-red-500/5 text-red-700 border-red-500/20'
                      }`}>
                        {log.status === 'COMPLETED' ? <CheckCircle className="h-2.5 w-2.5" /> : <AlertCircle className="h-2.5 w-2.5" />}
                        {log.status}
                      </span>
                    </td>
                    <td className="p-3 text-right text-muted-foreground tabular-nums">
                      <span className="text-foreground font-medium">{log.normalized_rows}</span> parsed • <span className="text-amber-600 font-medium">{log.suspicious_rows}</span> warnings • <span className="text-red-600 font-medium">{log.error_rows}</span> errors
                    </td>
                  </tr>
                ))}
                {uploads.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-12 text-muted-foreground font-medium">
                      No document packets recorded inside this processing frame registry.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}