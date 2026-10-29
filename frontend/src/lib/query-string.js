import {
  DEFAULT_API_BASE,
  DEFAULT_ORDERING,
  ORDERINGS,
  PAGE_SIZE,
} from "./constants.js";

/** The list state lives in the URL: ?industry=a&industry=b&ordering=-avg_rating&page=2 */
export function parseState(search) {
  const p = new URLSearchParams(search);
  const ordering = p.get("ordering");
  const page = Number.parseInt(p.get("page") ?? "", 10);
  return {
    industries: p.getAll("industry").filter(Boolean),
    ordering: ORDERINGS.some((o) => o.value === ordering)
      ? ordering
      : DEFAULT_ORDERING,
    page: page > 0 ? page : 1,
  };
}

/** Inverse of parseState; defaults are left out so the plain page keeps a clean URL. */
export function toSearch({ industries, ordering, page }) {
  const p = new URLSearchParams();
  for (const slug of industries) p.append("industry", slug);
  if (ordering !== DEFAULT_ORDERING) p.set("ordering", ordering);
  if (page > 1) p.set("page", String(page));
  const s = p.toString();
  return s ? `?${s}` : "";
}

/** The API request for a list state. */
export function apiUrl(state, apiBase = DEFAULT_API_BASE) {
  const p = new URLSearchParams();
  for (const slug of state.industries) p.append("industry", slug);
  p.set("ordering", state.ordering);
  p.set("page", String(state.page));
  p.set("page_size", String(PAGE_SIZE));
  return `${apiBase}?${p}`;
}
