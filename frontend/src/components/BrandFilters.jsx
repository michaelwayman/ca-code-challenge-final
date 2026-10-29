import { ORDERINGS } from "../lib/constants.js";

/** Industry checkboxes (chips) and the sort select. Controlled by the list state. */
export default function BrandFilters({ industries, state, onChange }) {
  const toggleIndustry = (slug) => {
    const set = new Set(state.industries);
    set.has(slug) ? set.delete(slug) : set.add(slug);
    onChange({ ...state, industries: [...set], page: 1 });
  };

  return (
    <form className="brand-filters" onSubmit={(e) => e.preventDefault()}>
      <fieldset>
        <legend>Industry</legend>
        {industries.map((ind) => (
          <label key={ind.slug} className="chip">
            <input
              type="checkbox"
              checked={state.industries.includes(ind.slug)}
              onChange={() => toggleIndustry(ind.slug)}
            />
            <span>{ind.name}</span>
          </label>
        ))}
      </fieldset>
      <div className="sort">
        <label htmlFor="brand-sort">Sort by</label>
        <select
          id="brand-sort"
          value={state.ordering}
          onChange={(e) =>
            onChange({ ...state, ordering: e.target.value, page: 1 })
          }
        >
          {ORDERINGS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}
