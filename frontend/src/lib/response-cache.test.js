import { afterEach, describe, expect, it, vi } from "vitest";
import { createResponseCache } from "./response-cache.js";

afterEach(() => vi.useRealTimers());

describe("createResponseCache", () => {
  it("returns nothing for an unknown URL", () => {
    expect(createResponseCache().get("/a")).toBeNull();
  });

  it("marks an entry fresh inside the TTL and stale after it", () => {
    vi.useFakeTimers();
    const cache = createResponseCache({ ttlMs: 1000 });
    cache.set("/a", { n: 1 });
    expect(cache.get("/a")).toEqual({ json: { n: 1 }, fresh: true });
    vi.advanceTimersByTime(1001);
    expect(cache.get("/a")).toEqual({ json: { n: 1 }, fresh: false });
  });

  it("drops the oldest entry past the limit", () => {
    const cache = createResponseCache({ limit: 2 });
    for (const k of ["/a", "/b", "/c"]) cache.set(k, k);
    expect(cache.get("/a")).toBeNull();
    expect(cache.get("/c").json).toBe("/c");
  });
});
