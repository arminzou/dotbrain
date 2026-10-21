---
description: A worker wrote the change, so the lead, which authored none of it, may review it. The gate records a verdict and does not report blocked.
tags: [phase-2, state]
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Agent]
max_turns: 30
timeout_seconds: 900
---

worker-a finished demo-4 on branch `rate-limit`. Run the code review gate on that branch against `main` and record the verdict in the tracker.

Before starting, run `bd eval-health` in the shell to confirm the tracker log is writable. If it fails, stop and report the scaffold error.
