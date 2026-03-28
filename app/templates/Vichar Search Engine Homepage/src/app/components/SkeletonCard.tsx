export function SkeletonCard() {
  return (
    <div className="py-5 animate-pulse">
      {/* URL */}
      <div className="h-3 w-40 bg-muted rounded mb-2" />

      {/* Title */}
      <div className="h-5 w-3/4 bg-muted rounded mb-2" />

      {/* Description */}
      <div className="h-4 w-full bg-muted rounded mb-1" />
      <div className="h-4 w-5/6 bg-muted rounded" />
    </div>
  );
}

