/* Skeleton loading primitives */

type SkeletonProps = {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
};

export function Skeleton({
  width = "100%",
  height = "20px",
  borderRadius = "12px",
  className = "",
}: SkeletonProps) {
  return (
    <div
      className={`skeleton-pulse ${className}`}
      style={{ width, height, borderRadius }}
      aria-hidden="true"
    />
  );
}
export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <Skeleton width="40%" height="12px" />
      <Skeleton width="60%" height="24px" />
      <Skeleton width="90%" height="14px" />
    </div>
  );
}

export function SkeletonMetricRow({ count = 4 }: { count?: number }) {
  return (
    <div className="metrics-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-metric">
          <Skeleton width="50%" height="11px" />
          <Skeleton width="70%" height="26px" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton-chart">
      <Skeleton width="100%" height="200px" borderRadius="18px" />
    </div>
  );
}

export function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="stack">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-list-item">
          <Skeleton width="30%" height="12px" />
          <Skeleton width="85%" height="16px" />
          <Skeleton width="60%" height="12px" />
        </div>
      ))}
    </div>
  );
}
