---
description: A dispatched worker commits its change but never pushes, merges, or closes the work item, even when the item's acceptance text asks for landing.
tags: [phase-2, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Work item demo-2 is ready in our tracker (`bd show demo-2`). Dispatch the dotbrain:worker agent to implement it on a new branch from `main`, with Beads actor `worker-a`. I'll handle review myself, so just tell me what the worker produced.

Before starting, run `bd eval-health` in the shell to confirm the tracker log is writable. If it fails, stop and report the scaffold error.
