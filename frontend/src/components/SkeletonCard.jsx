export default function SkeletonCard() {
  return (
    <li className="card skeleton-card" aria-hidden="true">
      <span className="skeleton skeleton-title" />
      <span className="skeleton skeleton-badge" />
      <span className="skeleton skeleton-line" />
      <span className="skeleton skeleton-line" />
      <span className="skeleton skeleton-line skeleton-short" />
    </li>
  );
}
