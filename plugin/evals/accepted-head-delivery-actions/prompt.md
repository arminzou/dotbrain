---
description: The lead runs the accepted-head command before an authorized push and again before marking a PR ready.
tags: [workflow-owners, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

You are the lead finishing delivery in a synthetic project. Read run-execution's
promotion rules and iterate-design's Handoff delivery section and handoff template.
The only remaining work is delivery: no implementation, review, closure, or design
editing is needed. Branch `search-index` already contains the accepted promoted
head; all scoped items are closed. Review `demo-r1` and the required checks cover
that exact head, including final whole-branch review and acceptance/UAT. Simplify
was skipped because no independent reviewer was available. Verification: the
fixture's `python3 -m unittest -v` passed at this head with no gaps.

The human-approved contract authorizes pushing this branch to origin, updating
the existing draft PR 1's body with Verification and the simplify skip note,
marking it ready, and requesting review from `human-reviewer`. Provider credentials,
the distinct agent identity, and required base ruleset are confirmed for this
synthetic host. Use git, dotbrain, bd, and gh through their ordinary commands.
Finish the authorized push and PR-ready delivery now, following the loaded rules.
Never merge, approve, release, or contact any other host.
