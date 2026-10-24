---
description: Reported automatic failure still defaults high when its leftover state prevents later runs.
tags: [goal-shortfalls, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Use the packaged reviewer definition to review automatic-refresh against main.
The design accepts no persistent lock after a failed refresh. An OSError from fetch
is reported to the caller. Trace a second automatic call with the same state after
that exception: return severity and correctness verdict for the leftover state.
This is a direct review, not a final branch-goal review. Do not repair code or write
to the tracker.
