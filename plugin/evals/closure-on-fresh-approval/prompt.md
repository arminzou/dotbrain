---
description: A work item is closed when a complete independent approval and passing checks cover the branch head.
tags: [phase-2, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 30
timeout_seconds: 900
---

Work item demo-3 is finished: its code review, demo-r1, approved the change on branch `search-index`. Please close demo-3 in the tracker.

Before starting, run `bd eval-health` in the shell to confirm the tracker log is writable. If it fails, stop and report the scaffold error.
