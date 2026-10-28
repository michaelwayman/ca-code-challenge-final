import { useCallback, useEffect, useState } from "react";
import { parseState, toSearch } from "./url.js";

/**
 * The list state, kept in the URL. `update(next)` pushes a history entry;
 * `update(next, { replace: true })` replaces the current one. Back/forward re-read the URL.
 */
export default function useUrlState() {
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
