import Stars from "./Stars.jsx";

export default function BrandCard({ brand }) {
  const { top_review: top } = brand;
  return (
    <li className="card">
      <h3>
        <a href={`/brand/${brand.slug}/`}>{brand.name}</a>
      </h3>
      {brand.industry && <span className="badge">{brand.industry.name}</span>}
      <Stars rating={brand.average_rating} />
      <span className="meta">
        {brand.review_count} review{brand.review_count === 1 ? "" : "s"}
      </span>
      <p className="excerpt">{brand.short_description}</p>
      {top && (
        <blockquote className="top-review">
          <a href={`/review/${top.slug}/`}>{top.title}</a>
          <p>{top.snippet}</p>
        </blockquote>
      )}
    </li>
  );
}
