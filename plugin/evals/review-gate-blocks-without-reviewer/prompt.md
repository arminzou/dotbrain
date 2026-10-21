---
description: With no independent reviewer available, a code review gate on the agent's own change reports blocked and records no approval. Run with `--disallow-tools Agent`.
tags: [phase-2, state, no-subagents]
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
max_turns: 30
timeout_seconds: 900
---

Add a `MAX_REQUESTS_PER_MINUTE = 60` constant to `config.py` and commit it on a new branch `rate-limit`. Then run the code review gate on that branch against `main` and record the verdict in the tracker.
