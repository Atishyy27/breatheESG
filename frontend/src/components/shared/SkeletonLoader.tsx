interface SkeletonLoaderProps {
  variant?: 'table' | 'dashboard';
}

export function SkeletonLoader({ variant = 'table' }: SkeletonLoaderProps) {
  if (variant === 'dashboard') {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-muted rounded-md w-1/4 animate-pulse mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-muted border border-border rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div className="h-64 bg-muted border border-border rounded-xl animate-pulse" />
          <div className="h-64 bg-muted border border-border rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  // Table variant for the Queue/Uploads pages later
  return (
    <div className="w-full space-y-3 p-4 border border-border rounded-xl bg-card">
      <div className="h-6 bg-muted animate-pulse rounded w-1/4 mb-6" />
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex gap-4 items-center border-b border-border pb-3">
          <div className="h-4 bg-muted animate-pulse rounded w-8" />
          <div className="h-4 bg-muted animate-pulse rounded flex-1" />
          <div className="h-4 bg-muted animate-pulse rounded w-24" />
          <div className="h-4 bg-muted animate-pulse rounded w-32" />
        </div>
      ))}
    </div>
  );
}