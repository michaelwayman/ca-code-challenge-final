export const DEFAULT_ORDERING = "name";
export const PAGE_SIZE = 6;

export const ORDERINGS = [
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
  { value: "-avg_rating", label: "Highest rated" },
  { value: "avg_rating", label: "Lowest rated" },
  { value: "-review_count", label: "Most reviews" },
  { value: "review_count", label: "Fewest reviews" },
];

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

export function toSearch({ industries, ordering, page }) {
  const p = new URLSearchParams();
  for (const slug of industries) p.append("industry", slug);
  if (ordering !== DEFAULT_ORDERING) p.set("ordering", ordering);
  if (page > 1) p.set("page", String(page));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function apiUrl(state, apiBase = "/api/brands/") {
  const p = new URLSearchParams();
  for (const slug of state.industries) p.append("industry", slug);
  p.set("ordering", state.ordering);
  p.set("page", String(state.page));
  p.set("page_size", String(PAGE_SIZE));
  return `${apiBase}?${p}`;
}

export const brandPath = (slug) => `/brand/${slug}/`;
export const reviewPath = (slug) => `/review/${slug}/`;
