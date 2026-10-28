<!--
Your own words for the README sections that ask for your opinion.
The readme-from-challenge skill copies this file into README.md verbatim and never rewrites it.
Edit the text below to change an answer; the skill picks it up on the next run.
Saved from the README as it stood on 2026-10-28.
-->

## Modeling decisions, what I'd do differently, and AI defaults

### Modeling decisions

- **The average rating is derived**, never stored, so it can't disagree with the reviews. The ACF value is kept only as `legacy_average_rating`.
- **Reviewers are a small profile table** keyed by the same deterministic id as the auth user. The migration and the user import can run independently, with no call between the two services.
- **The migration is an upsert** keyed on `wp_id` that mirrors WordPress, so it is safe to re-run.

### What I would do differently with more time

- **The features I left out were deliberate, not a lack of time.** I kept to the spec's out-of-scope list: no login UI, no registration or password reset, no image uploads, no pixel-matching the WP theme.
- **The README could be tighter.** I'd cut it down further.

With more time I would keep working on [mkit](https://github.com/michaelwayman/mkit). I built it, along with `mbuild`, to solve this challenge. I've now built several submissions with it, they all work, and each one helped me refine both plugins.

### Where I chose the AI's default.
DRF generics and page-number pagination, `select_related` / `prefetch_related` for N+1, React hooks with plain `fetch` and no data library, and a Vite library-mode bundle. Defaults I replaced: unbounded pagination, hash-only passwords, and trusting token claims without a version check.
