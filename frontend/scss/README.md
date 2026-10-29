# frontend/scss

Compile: `sass frontend/scss/main.scss` (or `make fe-build` in Docker). Tokens live only in `abstracts/_tokens.scss`.

## Layout

`abstracts/` tokens and mixins, `base/` reset and element defaults, `layout/` page structure, `components/` one partial per component, `pages/` page-specific rules, `utilities/` single-purpose helpers. `main.scss` `@use`s them in that order.

**New component:** add `components/_name.scss` and an `@use "components/name";` line in `main.scss`.

## Class naming convention

- Component names are flat: `.card`, `.badge`, `.pagination`, `.brand-list`. No BEM `__`/`--` suffixes.
- The component root class is the only top-level selector in its partial. Its parts are descendant selectors nested under the root (`.card { h3 {...} .meta {...} }`), so a rule never leaks to another component.
- State is a modifier class on the root or an ARIA attribute (`[aria-current="page"]`, `[disabled]`), not a new component name.
- Font sizes, spacing, colours and radii come from tokens (`var(--font-md)`, `var(--space-4)`); breakpoints are Sass variables (`$bp-mobile` 640px, `$bp-tablet` 900px) used via the `mobile` and `tablet` mixins.
