import { describe, expect, it } from "vitest";
import { pageItems, pagerItems } from "./pagination.js";

const shape = (cur, total) =>
  pageItems(cur, total).map((i) => (i.type === "gap" ? "…" : i.n));

describe("pageItems", () => {
  it("windows the page list with gaps", () => {
    expect(shape(8, 18)).toEqual([1, "…", 7, 8, 9, "…", 18]);
    expect(shape(1, 18)).toEqual([1, 2, 3, 4, 5, "…", 18]);
    expect(shape(4, 18)).toEqual([1, 2, 3, 4, 5, "…", 18]);
    expect(shape(18, 18)).toEqual([1, "…", 14, 15, 16, 17, 18]);
    expect(shape(15, 18)).toEqual([1, "…", 14, 15, 16, 17, 18]);
    expect(shape(3, 5)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe("pagerItems", () => {
  const phone = (cur, total) =>
    pagerItems(cur, total)
      .filter((i) => i.type === "gap" || !i.hiddenOnMobile)
      .map((i) => (i.type === "gap" ? "…" : i.n));

  it("never skips a page silently on a phone", () => {
    expect(phone(8, 18)).toEqual([1, "…", 8, "…", 18]);
    expect(phone(4, 18)).toEqual([1, "…", 4, "…", 18]);
    expect(phone(2, 18)).toEqual([1, 2, "…", 18]);
    expect(phone(1, 18)).toEqual([1, "…", 18]);
    expect(phone(18, 18)).toEqual([1, "…", 18]);
    expect(phone(3, 5)).toEqual([1, "…", 3, "…", 5]);
    expect(phone(2, 3)).toEqual([1, 2, 3]);
  });
});
