import { useState, useRef } from 'react';
import { FileUp, Loader2 } from 'lucide-react';

interface UploadZoneProps {
  onUpload: (file: File, type: string) => void;
  isProcessing: boolean;
}

export function UploadZone({ onUpload, isProcessing }: UploadZoneProps) {
  const [sourceType, setSourceType] = useState('SAP');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const execute = (e: React.FormEvent) => {
    e.preventDefault();
    if (file && sourceType) onUpload(file, sourceType);
    setFile(null); // Clear file after dispatch
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col h-full">
      <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Stream Configuration</h2>
      <form onSubmit={execute} className="flex flex-col flex-1 gap-4">
        <select 
          value={sourceType} 
          onChange={(e) => setSourceType(e.target.value)}
          className="w-full text-sm p-2.5 rounded-lg bg-background border border-border focus:ring-1 focus:ring-primary outline-none"
        >
          <option value="SAP">SAP Material Movements Export (CSV)</option>
          <option value="UTILITY_BILL">Utility Portal Summary Bills (CSV)</option>
          <option value="UTILITY_METER">Smart Meter Telemetry Stream (CSV)</option>
          <option value="TRAVEL">Concur Routine Expenses (JSON)</option>
        </select>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => { e.preventDefault(); setIsDragging(false); setFile(e.dataTransfer.files[0]); }}
          onClick={() => fileInputRef.current?.click()}
          className={`flex-1 border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-colors min-h-[160px] ${
            isDragging ? 'border-blue-500 bg-blue-500/5' : 'border-border bg-muted/20 hover:bg-muted/50'
          }`}
        >
          <input type="file" ref={fileInputRef} className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <FileUp className={`h-8 w-8 mb-3 ${file ? 'text-primary' : 'text-muted-foreground'}`} />
          <span className="text-sm font-medium text-foreground text-center">
            {file ? file.name : "Drag & drop corporate asset here"}
          </span>
          {!file && <span className="text-xs text-muted-foreground mt-1">or click to browse local directories</span>}
        </div>

        <button
          type="submit"
          disabled={!file || isProcessing}
          className="w-full py-2.5 bg-primary text-primary-foreground text-sm font-semibold rounded-lg disabled:opacity-50 hover:bg-primary/90 flex items-center justify-center gap-2 transition-all"
        >
          {isProcessing ? <><Loader2 className="h-4 w-4 animate-spin" /> Running Pipeline...</> : "Execute Ingestion"}
        </button>
      </form>
    </div>
  );
}