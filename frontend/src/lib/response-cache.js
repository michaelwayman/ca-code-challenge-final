/**
 * Small per-component cache of API responses keyed by URL. `get` says whether the entry is still
 * fresh (inside the TTL, so no request is needed) or stale (show it, then revalidate). The oldest
 * entry is dropped past `limit`.
 */
export function createResponseCache({ limit = 50, ttlMs = 30_000 } = {}) {
  const entries = new Map();
  return {
    get(url) {
      const entry = entries.get(url);
      if (!entry) return null;
      return { json: entry.json, fresh: Date.now() - entry.at < ttlMs };
    },
    set(url, json) {
      entries.delete(url);
      entries.set(url, { json, at: Date.now() });
      if (entries.size > limit) entries.delete(entries.keys().next().value);
    },
  };
}
