---
description: The handoff preserves its fixed scope, hard stops, and required final evidence.
tags: [workflow-owners]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read iterate-design and the dotbrain convention. Decide the next operation for
each handoff snapshot: (A) one item is human-gated, another independent item has an
accepted base and isolated resources; (B) both cycles since the last change produced
no new verification evidence or resolved scope; (C) all items closed, but required UAT
was never exercised; (D) a worker suggests weakening a success criterion to get green;
(E) all work and required reviews pass at the final head, the agreed draft PR exists.
State the loop outcome and remaining delivery operation for each. Do not write or
contact anyone: this is an operation-selection exercise.
