---
description: The lead preserves all checkpoint entries and actor ownership when recording a result.
tags: [workflow-owners]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read manage-work-graph. Return the exact tracker commands and comment-file text
you would use, without executing them. Worker-a owns task alpha. Its tests-pass streak
is 1/3 and item-review is 2/3. Tests now pass, while review has not rerun. Artifacts
contain work and candidate references. You are lead. Record tests passing, retaining
all other state. Then describe closure after acceptance, and replacement if worker-a
cannot resume but its termination is uncertain. Include the Windows-safe file-writing
method. Do not expose real private project information.

Does an expired claim lease allow another actor to take over? What changes if the
worker is confirmed stopped? Include the exact claim-move command and durable comment.
