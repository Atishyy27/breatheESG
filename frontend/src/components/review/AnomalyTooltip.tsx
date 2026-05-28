export function AnomalyTooltip({ code, details }: { code: string; details?: string | null }) {
  if (!code) return null;
  return (
    <div className="group relative inline-flex items-center">
      <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 rounded cursor-help">
        ⚠ {code.replace('_', ' ')}
      </span>
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-xs rounded shadow-lg z-50 pointer-events-none">
        {details || 'System anomaly detected by pipeline validation engine.'}
      </div>
    </div>
  );
}