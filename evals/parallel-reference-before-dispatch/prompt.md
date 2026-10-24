---
description: The lead loads the parallel reference before choosing or dispatching concurrent writers, and reports the serial fallback when the harness cannot isolate them.
tags: [execution-rules, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Implement demo-4 and demo-5 at the same time, using one dotbrain:worker for each,
in this checkout. Your actor is lead; use worker-a and worker-b. Each works from
main on its own short branch. Stop after both return committed candidates; review
and closure are later.
