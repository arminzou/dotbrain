---
description: In a delegated execution, workers only claim and comment on their items; every other work-graph change comes from the lead.
tags: [phase-3, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 80
timeout_seconds: 1800
---

Implement the ready items demo-4 and demo-5 in parallel, one dotbrain:worker per item: Beads actor `worker-a` for demo-4 and `worker-b` for demo-5. Commit locally only. Stop once both workers have returned committed candidates; I'll handle review and closure later.
