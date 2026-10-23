---
description: A dispatched worker stores its full report on its work item as a Candidate comment before it returns.
tags: [dispatch-records, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Dispatch the dotbrain:worker agent with exactly the assignment below, unchanged. When it
returns, reply with only the text it returned, verbatim, and nothing else. I'll handle review
myself.

**Item:** demo-2 · implement · actor worker-a
**Checkout:** in place, on the current branch `contributing-guide`
**Change:** Add CONTRIBUTING.md telling contributors to run `make test` before sending changes.
**Ownership:** CONTRIBUTING.md · the contributing guide · overlap: none
**Acceptance:** CONTRIBUTING.md exists and names `make test`.
**Checks:** `make test`
**Limits:** role default
**Constraints:** none
**Overrides:** none
**Sources:** `bd show demo-2`
