export default function Loading() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading page">
      <div className="space-y-3 border-b border-border pb-5">
        <div className="h-3 w-24 animate-pulse rounded bg-muted motion-reduce:animate-none" />
        <div className="h-8 w-56 animate-pulse rounded bg-muted motion-reduce:animate-none" />
        <div className="h-5 max-w-xl animate-pulse rounded bg-muted motion-reduce:animate-none" />
      </div>
      <div className="min-h-72 animate-pulse rounded-lg border border-border bg-card motion-reduce:animate-none" />
      <span className="sr-only">Loading</span>
    </div>
  );
}
