import { useNavigate } from 'react-router-dom'
import { ROLES, type Role, useRole } from '@/context/RoleContext'

export function RoleSelectPage() {
  const { setRole } = useRole()
  const navigate = useNavigate()

  const handleSelect = (role: Role) => {
    setRole(role)
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <div className="max-w-2xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3 mb-6">
            <span className="text-2xl font-bold">BreatheESG</span>
            <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded font-semibold">
              Workbench
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Select your role</h1>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            Choose how you'll interact with the carbon data ingestion platform.
            Each role has tailored permissions and workflows.
          </p>
        </div>

        {/* Role cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Object.values(ROLES).map(r => (
            <button
              key={r.id}
              onClick={() => handleSelect(r.id)}
              className="group relative text-left border border-border bg-card hover:border-primary/50 hover:bg-primary/5 rounded-xl p-6 transition-all duration-200 hover:shadow-md"
            >
              <div className="flex items-start gap-4">
                <div className="text-3xl">{r.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                    {r.label}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {r.description}
                  </div>

                  {/* Capability indicators */}
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {r.canUpload && <CapBadge label="Upload" />}
                    {r.canApprove && <CapBadge label="Approve" />}
                    {r.canBatchApprove && <CapBadge label="Batch Ops" color="amber" />}
                    {r.canExport && <CapBadge label="Export" />}
                    {!r.canApprove && !r.canUpload && <CapBadge label="Read Only" color="slate" />}
                  </div>
                </div>
              </div>

              {/* Arrow hint */}
              <div className="absolute top-5 right-5 text-muted-foreground group-hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
                →
              </div>
            </button>
          ))}
        </div>

        <p className="text-center text-xs text-muted-foreground">
          Prototype demonstration — no authentication required. Roles persist in local storage.
        </p>
      </div>
    </div>
  )
}

function CapBadge({
  label,
  color = 'blue',
}: {
  label: string
  color?: 'blue' | 'amber' | 'slate'
}) {
  const classes = {
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
  }[color]

  return (
    <span className={`px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border rounded ${classes}`}>
      {label}
    </span>
  )
}