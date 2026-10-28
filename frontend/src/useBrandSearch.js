import { useEffect, useRef, useState } from "react";
import { apiUrl } from "./url.js";

const CACHE_LIMIT = 50;
const CACHE_TTL_MS = 30_000; // matches max-age in the API's Cache-Control

/**
 * Fetch the brand page for `state`. Returns { data, status, retry } where status is
 *   "loading"    nothing to show yet (first load, or after an error)
 *   "refreshing" previous results on screen while new ones load
 *   "ready"      data is current (or a cached copy is being revalidated quietly)
 *   "error"      the request failed and there is nothing cached to show
 *
 * Responses are cached per URL for the life of the component: a cached URL is shown at once
 * and only refetched after 30s. Only the newest request may write state; a superseded
 * response is ignored. A 404 for a page past the end calls onPastLastPage.
 */
export default function useBrandSearch(
  state,
  { apiBase, fetchImpl, onPastLastPage },
) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(0);
  const cache = useRef(new Map());
  // Read through a ref so a new callback each render does not refetch.
  const pastLastPage = useRef(onPastLastPage);
  pastLastPage.current = onPastLastPage;

  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-runs the fetch on retry
  useEffect(() => {
    const id = ++latest.current;
    const controller = new AbortController();
    const url = apiUrl(state, apiBase);
    const entry = cache.current.get(url);
    if (entry) {
      setData(entry.json);
      setStatus("ready");
      if (Date.now() - entry.at < CACHE_TTL_MS) return undefined;
    } else {
      setStatus((s) =>
        s === "ready" || s === "refreshing" ? "refreshing" : "loading",
      );
    }
    (fetchImpl ?? fetch)(url, { signal: controller.signal })
      .then((r) => {
        if (id === latest.current && r.status === 404 && state.page > 1) {
          // A stale URL or back/forward past the end: go to page 1, not a dead error.
          pastLastPage.current();
          return null;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (id !== latest.current || json === null) return;
        remember(cache.current, url, json);
        setData(json);
        setStatus("ready");
      })
      .catch(() => {
        if (id !== latest.current) return;
        setStatus(entry ? "ready" : "error");
      });
    return () => controller.abort();
  }, [state, attempt, apiBase, fetchImpl]);

  return { data, status, retry: () => setAttempt((n) => n + 1) };
}

/** Store `json` as the newest entry, dropping the oldest past CACHE_LIMIT. */
function remember(cache, url, json) {
  cache.delete(url);
  cache.set(url, { json, at: Date.now() });
  if (cache.size > CACHE_LIMIT) cache.delete(cache.keys().next().value);
}
