import { pagerItems } from "../lib/pagination.js";

/** Numbered pager with Previous/Next; `onChange(page)` is called with the target page. */
export default function Pagination({ page, pages, onChange }) {
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="page-numbers page-nav"
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
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
            onClick={() => {
              if (item.n !== page) onChange(item.n);
            }}
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
        onClick={() => onChange(page + 1)}
      >
        <span className="page-nav-text">Next</span>
        <span aria-hidden="true">›</span>
      </button>
    </nav>
  );
}
