/**
 * Reusable loading spinner component.
 */
export function Spinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'w-5 h-5', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className={`${sizes[size]} ${className}`} role="status" aria-label="Loading">
      <svg className="animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-75" fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    </div>
  );
}

/**
 * Full-page loading state with spinner and optional message.
 */
export function LoadingScreen({ message }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Spinner size="lg" className="text-primary" />
      {message && <p className="text-text-secondary text-sm">{message}</p>}
    </div>
  );
}

/**
 * Skeleton loading placeholder.
 */
export function Skeleton({ className = '', lines = 1 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`skeleton h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'} ${className}`} />
      ))}
    </div>
  );
}

/**
 * Empty state placeholder.
 */
export function EmptyState({ icon = '📭', title, message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
      {message && <p className="text-text-secondary text-sm max-w-xs">{message}</p>}
    </div>
  );
}
