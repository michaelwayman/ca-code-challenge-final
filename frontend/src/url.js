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

/**
 * Page list for the pager: first and last always, the current page and one neighbour either
 * side, "gap" markers between. Near an end it shows 5 consecutive pages so a gap never hides
 * a single page. Returns [{type: "page", n} | {type: "gap", key}].
 */
export function pageItems(current, total) {
  const page = (n) => ({ type: "page", n });
  const range = (a, b) =>
    Array.from({ length: b - a + 1 }, (_, i) => page(a + i));
  if (total <= 7) return range(1, total);
  if (current <= 4) {
    return [...range(1, 5), { type: "gap", key: "gap-end" }, page(total)];
  }
  if (current >= total - 3) {
    return [
      page(1),
      { type: "gap", key: "gap-start" },
      ...range(total - 4, total),
    ];
  }
  return [
    page(1),
    { type: "gap", key: "gap-start" },
    ...range(current - 1, current + 1),
    { type: "gap", key: "gap-end" },
    page(total),
  ];
}
