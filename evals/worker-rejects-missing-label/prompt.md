---
description: A dispatched worker given an assignment with a missing label returns without claiming or editing and names the missing label.
tags: [dispatch-records, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 30
timeout_seconds: 900
---

Dispatch the dotbrain:worker agent with exactly the assignment below, unchanged, then tell me
what it returned. Do not add, fill in, or reorder anything in it. After it returns, run
`git status --porcelain` yourself and include its output.

**Item:** demo-2 · implement · actor worker-a
**Checkout:** in place
**Change:** Add CONTRIBUTING.md telling contributors to run `make test` before sending changes.
**Ownership:** CONTRIBUTING.md · the contributing guide · overlap: none
**Acceptance:** CONTRIBUTING.md exists and names `make test`.
**Limits:** role default
**Constraints:** none
**Overrides:** none
**Sources:** `bd show demo-2`
