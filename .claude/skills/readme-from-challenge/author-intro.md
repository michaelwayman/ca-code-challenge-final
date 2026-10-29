<!--
Your own words for the README section on working with mkit and mbuild.
The readme-from-challenge skill copies this file into README.md verbatim, at the top, and never rewrites it.
-->
## Working on this project: mkit and mbuild

This repo is built and maintained with two Claude Code plugins, **mkit** and **mbuild**, both in [github.com/michaelwayman/mkit](https://github.com/michaelwayman/mkit) (mbuild lives in its `mbuild/` folder). I developed them alongside this project, specifically for it, and they are required to work on it the way it is set up: `SPEC.md` is the source of truth and is changed only through them, never by hand. `CLAUDE.md` tells the agent the same. The app itself runs with Docker alone; the plugins are only for changing the code. Instead of one long chat, the agent works from the written spec, one small slice at a time, which keeps token use low and makes it hard to skip a requirement.

**What they bring**
- **Fewer tokens.** The agent reads a short index (`mkit show`) and only the items it needs (`mkit show R3`), never the whole spec.
- **Small, focused context.** `mkit brief` hands the builder just the requirements, constraints and out-of-scope items for one slice, and each slice runs in a fresh session, so context never snowballs.
- **Every requirement is checked.** Each requirement has acceptance bullets. A slice is only marked done (`mkit done`) after every bullet has been run as a command, request or test and passed.
- **Nothing gets lost.** `mkit status` shows what is done, open or reopened. Bugs and ideas go to an inbox (`mkit add`) instead of derailing the current slice.
- **No scope creep.** Out-of-scope items are explicit decisions, and anything beyond a requirement stops for a `/mkit:change`.
- **Independent review.** `/mbuild:review` checks the finished work against the spec in a fresh context.
- **A paper trail.** Decisions, plans and per-slice verification records live in `SPEC.md`, `.mbuild/plan.md` and `.mbuild/auto/`. How it went in practice is in [ai-workflow.md](ai-workflow.md).

To change something: log it with `mkit add "..." --bug|--feature|--adjust`, or run `/mkit:change` when it touches scope, then `/mbuild:build`.
