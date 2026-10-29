export const DEFAULT_ORDERING = "name";
export const PAGE_SIZE = 6;
export const DEFAULT_API_BASE = "/api/brands/";

export const ORDERINGS = [
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
  { value: "-avg_rating", label: "Highest rated" },
  { value: "avg_rating", label: "Lowest rated" },
  { value: "-review_count", label: "Most reviews" },
  { value: "review_count", label: "Fewest reviews" },
];
