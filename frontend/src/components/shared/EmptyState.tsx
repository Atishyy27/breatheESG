import { Database } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
}

export function EmptyState({ 
  title = "No Records Found", 
  description = "There is no data matching your current filters or queue state." 
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-border rounded-xl bg-card/50">
      <div className="w-12 h-12 bg-muted text-muted-foreground rounded-full flex items-center justify-center mb-4">
        <Database className="h-6 w-6" />
      </div>
      <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-xs mt-1">{description}</p>
    </div>
  );
}