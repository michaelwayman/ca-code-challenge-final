import { useBrandsQuery } from "../hooks/useBrandsQuery.js";
import { useUrlState } from "../hooks/useUrlState.js";
import { DEFAULT_API_BASE, PAGE_SIZE } from "../lib/constants.js";
import BrandFilters from "./BrandFilters.jsx";
import BrandResults from "./BrandResults.jsx";
import Pagination from "./Pagination.jsx";

/**
 * Filterable, sortable, paginated brand list. `industries` is [{slug, name}] for the checkboxes.
 * This component only wires the pieces: useUrlState owns the list state (URL-synced),
 * useBrandsQuery owns fetching and caching, the children render.
 */
export default function BrandList({
  industries = [],
  apiBase = DEFAULT_API_BASE,
  fetchImpl,
}) {
  const [state, update] = useUrlState();
  const firstPage = () => update({ ...state, page: 1 }, { replace: true });
  const { status, data, fetching, retry } = useBrandsQuery({
    state,
    apiBase,
    fetchImpl,
    onPageOverflow: firstPage,
  });

  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <div className="brand-list">
      <BrandFilters
        industries={industries}
        state={state}
        onChange={(next) => update(next, { replace: true })}
      />
      <BrandResults
        status={status}
        data={data}
        fetching={fetching}
        onRetry={retry}
        onClearFilters={() =>
          update({ ...state, industries: [], page: 1 }, { replace: true })
        }
      />
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
