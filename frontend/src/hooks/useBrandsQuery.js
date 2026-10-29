import { useEffect, useRef, useState } from "react";
import { apiUrl } from "../lib/query-string.js";
import { createResponseCache } from "../lib/response-cache.js";

/**
 * Fetches the brand page for `state`. Only the newest request may write state, so a superseded
 * response is ignored. A cached URL is shown at once and, once older than the TTL, revalidated
 * quietly; otherwise the previous results stay (`fetching`) until the response arrives.
 * `status` is "loading" until there is something to show, then "ready", or "error".
 * `onPageOverflow` is called when a page past the end 404s so the caller can fall back to page 1.
 */
export function useBrandsQuery({ state, apiBase, fetchImpl, onPageOverflow }) {
  const [status, setStatus] = useState("loading");
  const [data, setData] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(0);
  const cache = useRef(null);
  cache.current ??= createResponseCache();
  const overflow = useRef(onPageOverflow);
  overflow.current = onPageOverflow;

  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-runs the fetch on Retry
  useEffect(() => {
    const id = ++latest.current;
    const controller = new AbortController();
    const url = apiUrl(state, apiBase);
    const cached = cache.current.get(url);
    if (cached) {
      setData(cached.json);
      setStatus("ready");
      setFetching(false);
      if (cached.fresh) return undefined;
    } else {
      setStatus((s) => (s === "error" ? "loading" : s));
      setFetching(true);
    }
    (fetchImpl ?? fetch)(url, { signal: controller.signal })
      .then((r) => {
        if (id === latest.current && r.status === 404 && state.page > 1) {
          overflow.current();
          return null;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (id !== latest.current || json === null) return;
        cache.current.set(url, json);
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

  return { status, data, fetching, retry: () => setAttempt((n) => n + 1) };
}
