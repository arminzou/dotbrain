---
description: A contained design goal shortfall blocks the final review even though all item criteria pass.
tags: [goal-shortfalls, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Run review-gate's final whole-branch code review of theme-support against main
for epic demo-1, in the handoff workflow. Read the approved design at
.brain/designs/theme.md and record the verdict. Both child items met their own criteria.
The settings view's existing fallback is a contained medium finding with no data loss
or regression. Judge whether the branch delivers the approved goal. Do not change code,
push, merge, or mark a PR ready. Your actor is lead; fixture workers authored the diff.
