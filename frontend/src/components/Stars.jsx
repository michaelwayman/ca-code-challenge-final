export default function Stars({ rating }) {
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
