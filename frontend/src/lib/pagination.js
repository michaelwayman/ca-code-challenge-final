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

/**
 * pageItems plus what the phone layout needs. On a phone only the first, current and last pages
 * are shown; the rest get `hiddenOnMobile`. Where hidden pages sit between two visible pages
 * with no gap marker already there, a `mobileOnly` gap is added so a skipped page is never silent
 * (page 4 of 18 shows 1 … 4 … 18, not 1 4 … 18).
 */
export function pagerItems(current, total) {
  const out = [];
  let inRun = false; // inside a run of phone-hidden pages
  let pending = false; // that run needs a gap of its own (no desktop gap already sits at its start)
  for (const item of pageItems(current, total)) {
    if (item.type === "gap") {
      inRun = false;
      pending = false;
      out.push(item);
      continue;
    }
    const hiddenOnMobile =
      item.n !== 1 && item.n !== total && item.n !== current;
    if (hiddenOnMobile) {
      if (!inRun) pending = out.at(-1)?.type === "page";
      inRun = true;
    } else {
      if (pending)
        out.push({
          type: "gap",
          key: `gap-mobile-${item.n}`,
          mobileOnly: true,
        });
      inRun = false;
      pending = false;
    }
    out.push({ ...item, hiddenOnMobile });
  }
  return out;
}
