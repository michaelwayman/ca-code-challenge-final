import { describe, expect, it } from "vitest";
import { apiUrl, parseState, toSearch } from "./query-string.js";

describe("query-string", () => {
  it("parses industries, ordering and page, falling back to defaults", () => {
    expect(
      parseState("?industry=a&industry=b&ordering=-avg_rating&page=3"),
    ).toEqual({
      industries: ["a", "b"],
      ordering: "-avg_rating",
      page: 3,
    });
    expect(parseState("?ordering=bogus&page=-2")).toEqual({
      industries: [],
      ordering: "name",
      page: 1,
    });
  });

  it("leaves defaults out of the search string and round-trips the rest", () => {
    expect(toSearch({ industries: [], ordering: "name", page: 1 })).toBe("");
    const state = { industries: ["a"], ordering: "-review_count", page: 2 };
    expect(parseState(toSearch(state))).toEqual(state);
  });

  it("builds the API request with ordering, page and page_size", () => {
    const url = apiUrl({ industries: ["a"], ordering: "name", page: 2 }, "/x/");
    expect(url).toBe("/x/?industry=a&ordering=name&page=2&page_size=6");
  });
});
