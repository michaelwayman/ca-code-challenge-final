import { brandPath, reviewPath } from "./url.js";

/** Same markup and rounding as the {% stars %} tag in app/catalog/templatetags/display.py. */
export function Stars({ rating }) {
  if (rating == null) {
    return (
      <span className="stars">
        <span className="rating-value">No ratings yet</span>
      </span>
    );
  }
  const filled = Math.round(rating);
  return (
    <span
      className="stars"
      role="img"
      aria-label={`Rated ${rating.toFixed(1)} out of 5`}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={i < filled ? "star-full" : "star-empty"}
          aria-hidden="true"
        >
          ★
        </span>
      ))}
      <span className="rating-value" aria-hidden="true">
        {rating.toFixed(1)}
      </span>
    </span>
  );
}

export function BrandCard({ brand }) {
  const { top_review: top } = brand;
  return (
    <li className="card">
      <h3>
        <a href={brandPath(brand.slug)}>{brand.name}</a>
      </h3>
      {brand.industry && <span className="badge">{brand.industry.name}</span>}
      <Stars rating={brand.average_rating} />
      <span className="meta">
        {brand.review_count} review{brand.review_count === 1 ? "" : "s"}
      </span>
      <p className="excerpt">{brand.short_description}</p>
      {top && (
        <blockquote className="top-review">
          <a href={reviewPath(top.slug)}>{top.title}</a>
          <p>{top.snippet}</p>
        </blockquote>
      )}
    </li>
  );
}

export function SkeletonCard() {
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
