---
description: In a delegated execution, workers only claim and comment on their items; every other work-graph change comes from the lead. The eval harness has no worktree isolation, so the workers run one at a time in the shared checkout.
tags: [phase-3, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 80
timeout_seconds: 1800
---

Implement the ready items demo-4 and demo-5 with one dotbrain:worker per item, one after the other in this checkout: Beads actor `worker-a` for demo-4 and `worker-b` for demo-5, each on its own item branch from `main`. Your own Beads actor as lead is `lead`. Commit locally only. Stop once both workers have returned committed candidates; I'll handle review and closure later.
