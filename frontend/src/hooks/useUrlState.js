import { useCallback, useEffect, useState } from "react";
import { parseState, toSearch } from "../lib/query-string.js";

/**
 * List state (industries, ordering, page) kept in the URL. `update` replaces the history entry
 * for filter and sort changes (back leaves the view) and pushes one for page changes;
 * popstate (back/forward) re-reads the URL.
 */
export function useUrlState() {
  const [state, setState] = useState(() => parseState(window.location.search));

  useEffect(() => {
    const onPop = () => setState(parseState(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const update = useCallback((next, { replace = false } = {}) => {
    window.history[replace ? "replaceState" : "pushState"](
      null,
      "",
      `${window.location.pathname}${toSearch(next)}`,
    );
    setState(next);
  }, []);

  return [state, update];
}
