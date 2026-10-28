import { useCallback, useEffect, useRef, useState } from "react";
import { ORDERINGS, PAGE_SIZE, apiUrl, parseState, toSearch } from "./url.js";

function Stars({ rating }) {
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

function BrandCard({ brand }) {
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

/**
 * Filterable, sortable brand list. `industries` is [{slug, name}] for the checkboxes.
 * State is URL-synced (history.pushState; popstate re-fetches).
 */
export default function BrandList({
  industries = [],
  apiBase = "/api/brands/",
  fetchImpl,
}) {
  const [state, setState] = useState(() => parseState(window.location.search));
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [data, setData] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const onPop = () => setState(parseState(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // Only the newest request may write state: a superseded response is ignored.
  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-runs the fetch on Retry
  useEffect(() => {
    const id = ++latest.current;
    const controller = new AbortController();
    setStatus("loading");
    (fetchImpl ?? fetch)(apiUrl(state, apiBase), { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (id !== latest.current) return;
        setData(json);
        setStatus("ready");
      })
      .catch(() => {
        if (id !== latest.current) return;
        setStatus("error");
      });
    return () => controller.abort();
  }, [state, attempt, apiBase, fetchImpl]);

  const update = useCallback((next) => {
    window.history.pushState(
      null,
      "",
      `${window.location.pathname}${toSearch(next)}`,
    );
    setState(next);
  }, []);

  const toggleIndustry = (slug) => {
    const set = new Set(state.industries);
    set.has(slug) ? set.delete(slug) : set.add(slug);
    update({ ...state, industries: [...set], page: 1 });
  };

  const clearFilters = () => update({ ...state, industries: [], page: 1 });
  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const results = data?.results ?? [];

  return (
    <div className="brand-list">
      <form className="brand-filters" onSubmit={(e) => e.preventDefault()}>
        <fieldset>
          <legend>Industry</legend>
          {industries.map((ind) => (
            <label key={ind.slug} className="check">
              <input
                type="checkbox"
                checked={state.industries.includes(ind.slug)}
                onChange={() => toggleIndustry(ind.slug)}
              />
              {ind.name}
            </label>
          ))}
        </fieldset>
        <div className="sort">
          <label htmlFor="brand-sort">Sort by</label>
          <select
            id="brand-sort"
            value={state.ordering}
            onChange={(e) =>
              update({ ...state, ordering: e.target.value, page: 1 })
            }
          >
            {ORDERINGS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </form>

      <section
        aria-labelledby="brand-results-heading"
        aria-live="polite"
        aria-busy={status === "loading"}
      >
        <h2 id="brand-results-heading">
          Brands{status === "ready" && data ? ` (${data.count})` : ""}
        </h2>
        {status === "loading" && (
          <output className="state-message">Loading brands…</output>
        )}
        {status === "error" && (
          <div className="state-message state-error" role="alert">
            <p>Could not load brands.</p>
            <button type="button" onClick={() => setAttempt((n) => n + 1)}>
              Retry
            </button>
          </div>
        )}
        {status === "ready" && results.length === 0 && (
          <div className="state-message">
            <p>No brands match these filters.</p>
            <button type="button" onClick={clearFilters}>
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

      {status === "ready" && pages > 1 && (
        <nav className="pagination" aria-label="Pagination">
          <button
            type="button"
            className="page-numbers"
            disabled={state.page <= 1}
            onClick={() => update({ ...state, page: state.page - 1 })}
          >
            Previous
          </button>
          <span className="page-numbers current" aria-current="page">
            Page {state.page} of {pages}
          </span>
          <button
            type="button"
            className="page-numbers"
            disabled={state.page >= pages}
            onClick={() => update({ ...state, page: state.page + 1 })}
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
