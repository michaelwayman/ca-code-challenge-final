import { PAGE_SIZE } from "../lib/constants.js";
import BrandCard from "./BrandCard.jsx";
import SkeletonCard from "./SkeletonCard.jsx";

const SKELETONS = Array.from({ length: PAGE_SIZE }, (_, i) => i);

/** The live results region: skeletons, dimmed-while-fetching, error, empty and the card grid. */
export default function BrandResults({
  status,
  data,
  fetching,
  onRetry,
  onClearFilters,
}) {
  const results = data?.results ?? [];
  const busy = fetching && status === "ready";

  return (
    <section
      aria-labelledby="brand-results-heading"
      aria-live="polite"
      aria-busy={status === "loading" || fetching}
      className={busy ? "results is-fetching" : "results"}
    >
      <h2 id="brand-results-heading">
        Brands{data && status !== "error" ? ` (${data.count})` : ""}
      </h2>
      {status === "loading" && (
        <>
          <output className="visually-hidden">Loading brands…</output>
          <ul className="grid brand-grid" aria-hidden="true">
            {SKELETONS.map((i) => (
              <SkeletonCard key={i} />
            ))}
          </ul>
        </>
      )}
      {busy && (
        <>
          <output className="visually-hidden">Updating results…</output>
          <span className="spinner" aria-hidden="true" />
        </>
      )}
      {status === "error" && (
        <div className="state-message state-error" role="alert">
          <p>Could not load brands.</p>
          <button type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}
      {status === "ready" && results.length === 0 && (
        <div className="state-message">
          <p>No brands match these filters.</p>
          <button type="button" onClick={onClearFilters}>
            Clear filters
          </button>
        </div>
      )}
      {status === "ready" && results.length > 0 && (
        <ul className="grid brand-grid">
          {results.map((b) => (
            <BrandCard key={b.slug} brand={b} />
          ))}
        </ul>
      )}
    </section>
  );
}
