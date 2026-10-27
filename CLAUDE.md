<!-- mkit -->
## mkit
SPEC.md holds scope, constraints and decisions (IDs: R requirement, S service or layer, O out of scope, A assumption, C constraint, Q question, T technology). Never read it whole: `mkit show` = index, `mkit show R3 O1` = just those items.

When to use what:
- Before building anything non-trivial: `mkit brief R<n>`; build only what it lists. If `mkit frame` shows a Stage other than done, framing is unfinished: do not build, continue `/mkit:frame`.
- User reports a bug, idea or tweak: `mkit add "<one line>" --bug|--feature|--adjust`, then carry on. Do not edit SPEC.md.
- A request touches an O item or goes beyond an R's acceptance: stop and ask; suggest `/mkit:change`. Do not build it.
- Scope, a constraint or a tech choice is unclear: ask, or `/mkit:research`. Do not guess.
- Design decisions (schema, API shape, service boundaries, libraries) are the user's: ask with a recommendation, then record it (`mkit apply "ANSWER Q<n> | text | Why: ..."`, By: delegated if they say "you decide").
- If the separate mbuild plugin is installed, it builds from the spec: `/mbuild:build` (slices), `/mbuild:run` (merges, migrations, waits), `/mbuild:review`.
- User corrects you: `/mkit:learn`. Said "triage": `/mkit:triage`. New project or big feature with no SPEC.md: suggest `/mkit:frame` (staged: brief, architecture, requirements, confirm; it waits for the user's `ready` at each stage).
- A requirement's acceptance changed after it was built: `mkit status` shows it `reopened`.
- You assumed something the spec doesn't cover: `mkit add "assumed X" --adjust`.

Change SPEC.md only through `mkit apply` or `/mkit:change`, never by hand.
<!-- mkit -->
