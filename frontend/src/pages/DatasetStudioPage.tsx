// frontend/src/pages/DatasetStudioPage.tsx
import { useState } from 'react'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'
import { Download, Sliders, Zap, Database } from 'lucide-react'

const PRESETS = [
  { id: 'clean', label: 'Clean Demo', icon: '✓', desc: '100 rows, 0% anomalies, known facilities', rows: 100, anomaly: 0 },
  { id: 'realistic', label: 'Realistic', icon: '⚡', desc: '500 rows, 8% anomalies, mixed sources', rows: 500, anomaly: 0.08 },
  { id: 'audit_prep', label: 'Audit Prep', icon: '📋', desc: '300 rows, 5% anomalies, all scopes covered', rows: 300, anomaly: 0.05 },
  { id: 'stress', label: 'Stress Test', icon: '🔥', desc: '2000 rows, 25% anomalies, maximum entropy', rows: 2000, anomaly: 0.25 },
]

const SOURCES = [
  { id: 'SAP', label: 'SAP Material Movements', ext: '.csv', icon: '🏭', desc: 'MBLNR/BUDAT flat file — German headers, mixed units, movement codes' },
  { id: 'SAP_FUEL', label: 'SAP Fuel Procurement', ext: '.csv', icon: '⛽', desc: 'Scope 1 fuel entries — diesel, heavy oil, natural gas' },
  { id: 'UTILITY_BILL', label: 'Utility Monthly Bills', ext: '.csv', icon: '⚡', desc: 'Billing periods spanning months — peak/offpeak split, demand charges' },
  { id: 'UTILITY_METER', label: 'Smart Meter Telemetry', ext: '.csv', icon: '📡', desc: 'Hourly interval data with timezone offsets and quality flags' },
  { id: 'TRAVEL', label: 'Concur Travel Expenses', ext: '.json', icon: '✈️', desc: 'IATA airport codes, cabin classes, hotel nights, ground transport' },
]

export function DatasetStudioPage() {
  const [source, setSource] = useState('SAP')
  const [rows, setRows] = useState(100)
  const [anomalyRate, setAnomalyRate] = useState(0.05)
  const [isGenerating, setIsGenerating] = useState(false)

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setRows(preset.rows)
    setAnomalyRate(preset.anomaly)
  }

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const response = await apiClient.post('/generate/', {
        source_type: source,
        row_count: rows,
        anomaly_rate: anomalyRate,
      }, { responseType: 'blob' })

      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      const src = SOURCES.find(s => s.id === source)
      a.download = `breathe_${source.toLowerCase()}_${rows}rows.${src?.ext?.replace('.', '') ?? 'csv'}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Dataset generated', {
        description: `${rows} rows with ${Math.round(anomalyRate * 100)}% anomaly injection`,
      })
    } catch (e: any) {
      toast.error('Generation failed', {
        description: e.response?.data?.error ?? 'Generator script error — check console',
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const selectedSrc = SOURCES.find(s => s.id === source)

  return (
    <div className="space-y-6 animate-in fade-in duration-300 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Database className="h-6 w-6 text-primary" />
          Dataset Generation Studio
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Generate realistic enterprise ESG datasets using the parametric generation engine.
          Wraps 20+ generator scripts with anomaly injection, corruption controls, and temporal realism.
        </p>
      </div>

      {/* Presets */}
      <div className="border border-border bg-card rounded-xl p-5">
        <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4" /> Scenario Presets
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {PRESETS.map(p => (
            <button
              key={p.id}
              onClick={() => applyPreset(p)}
              className="text-left border border-border rounded-lg p-3 hover:border-primary/40 hover:bg-primary/5 transition-all"
            >
              <div className="text-xl mb-1">{p.icon}</div>
              <div className="text-xs font-semibold">{p.label}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">{p.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Source selector */}
        <div className="border border-border bg-card rounded-xl p-5">
          <h2 className="text-sm font-bold mb-3">Source Type</h2>
          <div className="space-y-2">
            {SOURCES.map(s => (
              <label
                key={s.id}
                className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer border transition-all ${
                  source === s.id
                    ? 'border-primary/50 bg-primary/5'
                    : 'border-border hover:border-border/80 hover:bg-muted/20'
                }`}
              >
                <input
                  type="radio"
                  name="source"
                  value={s.id}
                  checked={source === s.id}
                  onChange={() => setSource(s.id)}
                  className="mt-0.5"
                />
                <div>
                  <div className="text-xs font-semibold flex items-center gap-2">
                    {s.icon} {s.label}
                    <span className="font-mono text-muted-foreground">{s.ext}</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{s.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Sliders */}
        <div className="border border-border bg-card rounded-xl p-5">
          <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
            <Sliders className="h-4 w-4" /> Generation Parameters
          </h2>

          <div className="space-y-6">
            {/* Row count */}
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="font-semibold">Row Count</span>
                <span className="font-mono font-bold">{rows.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min={10}
                max={2000}
                step={10}
                value={rows}
                onChange={e => setRows(Number(e.target.value))}
                className="w-full accent-primary"
              />
              <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
                <span>10</span><span>500</span><span>1000</span><span>2000</span>
              </div>
            </div>

            {/* Anomaly rate */}
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="font-semibold">Anomaly Injection Rate</span>
                <span className={`font-mono font-bold ${
                  anomalyRate > 0.15 ? 'text-red-500'
                  : anomalyRate > 0.05 ? 'text-amber-500'
                  : 'text-emerald-500'
                }`}>
                  {Math.round(anomalyRate * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={0.5}
                step={0.01}
                value={anomalyRate}
                onChange={e => setAnomalyRate(Number(e.target.value))}
                className="w-full accent-amber-500"
              />
              <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
                <span>Clean (0%)</span><span>Realistic (8%)</span><span>Stress (50%)</span>
              </div>
            </div>

            {/* Summary */}
            <div className="border border-border rounded-lg p-3 bg-muted/20">
              <div className="text-xs font-semibold mb-2">Generation Preview</div>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Source format</span>
                  <span className="font-mono font-semibold text-foreground">{selectedSrc?.label}</span>
                </div>
                <div className="flex justify-between">
                  <span>Output file</span>
                  <span className="font-mono text-foreground">{selectedSrc?.ext}</span>
                </div>
                <div className="flex justify-between">
                  <span>Estimated anomalies</span>
                  <span className={`font-mono font-semibold ${anomalyRate > 0.1 ? 'text-amber-500' : 'text-foreground'}`}>
                    ~{Math.round(rows * anomalyRate)} rows
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={isGenerating}
        className="w-full py-3 bg-primary text-primary-foreground font-semibold rounded-xl flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 transition-all shadow-md"
      >
        {isGenerating ? (
          <>
            <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Download className="h-4 w-4" />
            Generate & Download Dataset
          </>
        )}
      </button>
    </div>
  )
}