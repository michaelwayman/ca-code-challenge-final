import { pagerItems } from "./pager.js";

/** Previous / page numbers / Next. Calls onChange(n) only for a different page. */
export default function Pagination({ page, pages, onChange }) {
  const go = (n) => {
    if (n !== page) onChange(n);
  };
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="page-numbers page-nav"
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => go(page - 1)}
      >
        <span aria-hidden="true">‹</span>
        <span className="page-nav-text">Previous</span>
      </button>
      {pagerItems(page, pages).map((item) =>
        item.type === "gap" ? (
          <span
            key={item.key}
            className={`page-gap${item.mobileOnly ? " page-gap-mobile" : ""}`}
            aria-hidden="true"
          >
            …
          </span>
        ) : (
          <button
            key={item.n}
            type="button"
            className={`page-numbers page-number${
              item.n === page ? " current" : ""
            }${item.hiddenOnMobile ? " page-neighbour" : ""}`}
            aria-label={`Page ${item.n}`}
            aria-current={item.n === page ? "page" : undefined}
            onClick={() => go(item.n)}
          >
            {item.n}
          </button>
        ),
      )}
      <button
        type="button"
        className="page-numbers page-nav"
        aria-label="Next page"
        disabled={page >= pages}
        onClick={() => go(page + 1)}
      >
        <span className="page-nav-text">Next</span>
        <span aria-hidden="true">›</span>
      </button>
    </nav>
  );
}
