---
description: The final gate requires whole-branch coverage and closes reviews on evidence and dispositions.
tags: [workflow-owners]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read review-gate and its review-beads reference. You are the lead deciding whether
to mark a two-item handoff ready. Only the latest integration group has APPROVE; the
first group was reviewed at an older head. No report covers their interactions or the
full branch range. The mechanical gate passed at the current head. A simplify pass has
two suggestions, neither dispositioned. Explain the next review operations, what may
close before merge, what keeps the simplify bead open, and the PR-body summary.
Then consider the same facts on a single-item branch and in HITL without a simplify request.
Return decisions only; do not mutate files or contact a host.
