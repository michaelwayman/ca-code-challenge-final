# How I used AI

I built this with Claude Code and two small plugins I wrote: **mkit** and **mbuild** ([github.com/michaelwayman/mkit](https://github.com/michaelwayman/mkit)). I wrote them specifically to solve this assignment, and most of my time went into developing them, not into the app itself. The goal was cheap spec-driven development: have the AI work from written requirements instead of a long chat I'd have to keep re-explaining.

**Spec first (mkit).** Before any code, `/mkit:frame` walked me through brief, architecture and requirements, and waited for my `ready` at each step. The result is `SPEC.md`: numbered requirements with acceptance bullets, constraints, an out-of-scope list, and my decisions with reasons. The design calls were mine. The AI gave options with a recommendation and I picked.

**Build from the spec (mbuild).** `/mbuild:build` splits the requirements into slices and builds one at a time from a short brief. It checks every acceptance bullet (tests, commands, screenshots at 375px and 1280px) before marking anything done. It doesn't touch the spec while building. If it hits a gap, it logs it and I decide.

**Changing my mind.** I changed things a lot after the first build: no history entries on filter changes, better-looking filters, no flashing while loading, caching, numbered pagination. Each time I said it in plain words, `/mkit:change` turned it into a small spec edit, and I approved it before anything was written. Editing a built requirement marks it `reopened`, so nothing stays "done" by accident.

**What mkit is good at.** Getting requirements pinned down cheaply. The AI reads a short index and pulls only the items it needs, never the whole spec, so it uses few tokens. It also catches scope creep against the out-of-scope list and leaves a written trail of what was decided and why. I'd use it again on any project where the requirements matter.

I made the decisions and approved every change. The AI did the typing and the checking.
