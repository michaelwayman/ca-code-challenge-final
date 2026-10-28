import { useCallback, useEffect, useRef, useState } from "react";
import {
  ORDERINGS,
  PAGE_SIZE,
  apiUrl,
  pagerItems,
  parseState,
  toSearch,
} from "./url.js";

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

const CACHE_LIMIT = 50;
const CACHE_TTL_MS = 30_000; // matches max-age in the API's Cache-Control (R6)

function SkeletonCard() {
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

/**
 * Filterable, sortable brand list. `industries` is [{slug, name}] for the checkboxes.
 * State is URL-synced: filter and sort changes replaceState (no history entry),
 * page changes pushState; popstate re-fetches. Results are cached per URL for the life of
 * the component (no request within 30s, then shown and revalidated); a refetch keeps the previous results on screen (dimmed) until the new ones land.
 */
export default function BrandList({
  industries = [],
  apiBase = "/api/brands/",
  fetchImpl,
}) {
  const [state, setState] = useState(() => parseState(window.location.search));
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [data, setData] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(0);
  const cache = useRef(new Map());

  useEffect(() => {
    const onPop = () => setState(parseState(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // Only the newest request may write state: a superseded response is ignored.
  // A cached URL is shown at once and revalidated quietly; otherwise the previous results
  // stay put (dimmed) until the response arrives. Skeletons only when there is nothing to show.
  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-runs the fetch on Retry
  useEffect(() => {
    const id = ++latest.current;
    const controller = new AbortController();
    const url = apiUrl(state, apiBase);
    const entry = cache.current.get(url);
    const cached = entry?.json;
    if (cached) {
      setData(cached);
      setStatus("ready");
      setFetching(false);
      if (Date.now() - entry.at < CACHE_TTL_MS) return undefined;
    } else {
      setStatus((s) => (s === "error" ? "loading" : s));
      setFetching(true);
    }
    (fetchImpl ?? fetch)(url, { signal: controller.signal })
      .then((r) => {
        if (id === latest.current && r.status === 404 && state.page > 1) {
          // A page past the end (stale URL, back/forward): fall back to page 1, not a dead error.
          const first = { ...state, page: 1 };
          window.history.replaceState(
            null,
            "",
            `${window.location.pathname}${toSearch(first)}`,
          );
          setState(first);
          return null;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (id !== latest.current || json === null) return;
        const entries = cache.current;
        entries.delete(url);
        entries.set(url, { json, at: Date.now() });
        if (entries.size > CACHE_LIMIT) {
          entries.delete(entries.keys().next().value);
        }
        setData(json);
        setStatus("ready");
        setFetching(false);
      })
      .catch(() => {
        if (id !== latest.current) return;
        setFetching(false);
        if (!cached) setStatus("error");
      });
    return () => controller.abort();
  }, [state, attempt, apiBase, fetchImpl]);

  const update = useCallback((next, { replace = false } = {}) => {
    window.history[replace ? "replaceState" : "pushState"](
      null,
      "",
      `${window.location.pathname}${toSearch(next)}`,
    );
    setState(next);
  }, []);

  const toggleIndustry = (slug) => {
    const set = new Set(state.industries);
    set.has(slug) ? set.delete(slug) : set.add(slug);
    update({ ...state, industries: [...set], page: 1 }, { replace: true });
  };

  const clearFilters = () =>
    update({ ...state, industries: [], page: 1 }, { replace: true });
  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const results = data?.results ?? [];

  return (
    <div className="brand-list">
      <form className="brand-filters" onSubmit={(e) => e.preventDefault()}>
        <fieldset>
          <legend>Industry</legend>
          {industries.map((ind) => (
            <label key={ind.slug} className="chip">
              <input
                type="checkbox"
                checked={state.industries.includes(ind.slug)}
                onChange={() => toggleIndustry(ind.slug)}
              />
              <span>{ind.name}</span>
            </label>
          ))}
        </fieldset>
        <div className="sort">
          <label htmlFor="brand-sort">Sort by</label>
          <select
            id="brand-sort"
            value={state.ordering}
            onChange={(e) =>
              update(
                { ...state, ordering: e.target.value, page: 1 },
                { replace: true },
              )
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
        aria-busy={status === "loading" || fetching}
        className={
          fetching && status === "ready" ? "results is-fetching" : "results"
        }
      >
        <h2 id="brand-results-heading">
          Brands{data && status !== "error" ? ` (${data.count})` : ""}
        </h2>
        {status === "loading" && (
          <>
            <output className="visually-hidden">Loading brands…</output>
            <ul className="grid brand-grid" aria-hidden="true">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </ul>
          </>
        )}
        {fetching && status === "ready" && (
          <>
            <output className="visually-hidden">Updating results…</output>
            <span className="spinner" aria-hidden="true" />
          </>
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

      {data && status !== "error" && pages > 1 && (
        <nav className="pagination" aria-label="Pagination">
          <button
            type="button"
            className="page-numbers page-nav"
            aria-label="Previous page"
            disabled={state.page <= 1}
            onClick={() => update({ ...state, page: state.page - 1 })}
          >
            <span aria-hidden="true">‹</span>
            <span className="page-nav-text">Previous</span>
          </button>
          {pagerItems(state.page, pages).map((item) =>
            item.type === "gap" ? (
              <span
                key={item.key}
                className={`page-gap${item.mobileOnly ? " page-gap-mobile" : ""}`}
                aria-hidden="true"
              >
                …
              </span>
            ) : (
              <button
                key={item.n}
                type="button"
                className={`page-numbers page-number${
                  item.n === state.page ? " current" : ""
                }${item.hiddenOnMobile ? " page-neighbour" : ""}`}
                aria-label={`Page ${item.n}`}
                aria-current={item.n === state.page ? "page" : undefined}
                onClick={() => {
                  if (item.n !== state.page) update({ ...state, page: item.n });
                }}
              >
                {item.n}
              </button>
            ),
          )}
          <button
            type="button"
            className="page-numbers page-nav"
            aria-label="Next page"
            disabled={state.page >= pages}
            onClick={() => update({ ...state, page: state.page + 1 })}
          >
            <span className="page-nav-text">Next</span>
            <span aria-hidden="true">›</span>
          </button>
        </nav>
      )}
    </div>
  );
}
