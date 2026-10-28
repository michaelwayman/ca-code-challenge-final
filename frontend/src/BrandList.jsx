import { BrandCard, SkeletonCard } from "./BrandCard.jsx";
import Pagination from "./Pagination.jsx";
import { ORDERINGS, PAGE_SIZE } from "./url.js";
import useBrandSearch from "./useBrandSearch.js";
import useUrlState from "./useUrlState.js";

/**
 * Filterable, sortable brand list. `industries` is [{slug, name}] for the checkboxes.
 * State lives in the URL: filter and sort changes replace the history entry, page changes
 * push one. A refetch keeps the previous results on screen (dimmed) until the new ones land.
 */
export default function BrandList({
  industries = [],
  apiBase = "/api/brands/",
  fetchImpl,
}) {
  const [state, update] = useUrlState();
  const { data, status, retry } = useBrandSearch(state, {
    apiBase,
    fetchImpl,
    onPastLastPage: () => update({ ...state, page: 1 }, { replace: true }),
  });

  // Filter and sort changes start again at page 1 and leave no history entry.
  const refine = (changes) =>
    update({ ...state, ...changes, page: 1 }, { replace: true });

  const toggleIndustry = (slug) => {
    const set = new Set(state.industries);
    set.has(slug) ? set.delete(slug) : set.add(slug);
    refine({ industries: [...set] });
  };

  const showing = data && status !== "error" && status !== "loading";
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
            onChange={(e) => refine({ ordering: e.target.value })}
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
        aria-busy={status === "loading" || status === "refreshing"}
        className={status === "refreshing" ? "results is-fetching" : "results"}
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
        {status === "refreshing" && (
          <>
            <output className="visually-hidden">Updating results…</output>
            <span className="spinner" aria-hidden="true" />
          </>
        )}
        {status === "error" && (
          <div className="state-message state-error" role="alert">
            <p>Could not load brands.</p>
            <button type="button" onClick={retry}>
              Retry
            </button>
          </div>
        )}
        {showing && results.length === 0 && (
          <div className="state-message">
            <p>No brands match these filters.</p>
            <button type="button" onClick={() => refine({ industries: [] })}>
              Clear filters
            </button>
          </div>
        )}
        {showing && results.length > 0 && (
          <ul className="grid brand-grid">
            {results.map((b) => (
              <BrandCard key={b.slug} brand={b} />
            ))}
          </ul>
        )}
      </section>

      {data && status !== "error" && pages > 1 && (
        <Pagination
          page={state.page}
          pages={pages}
          onChange={(page) => update({ ...state, page })}
        />
      )}
    </div>
  );
}
