---
description: The lead loads the parallel reference before starting its second writing worker, even when both workers run sequentially.
tags: [execution-rules, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Implement demo-4 and demo-5, using one dotbrain:worker for each, sequentially in
this checkout (the harness cannot isolate native subagents). Your actor is lead; use
worker-a and worker-b. Each works from main on its own short branch. Stop after both
return committed candidates; review and closure are later. Before starting the second
writer, report the reference you loaded and the first writer's completion state.
