---
description: The automatic-failure default respects a failure mode explicitly accepted by the design.
tags: [goal-shortfalls]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read run-execution's review verdict rules and review-gate's final review rules.
Consider a change to a session-start diagnostic hook. The approved design's Failure
Modes section says: "When the external service is unreachable, the hook exits 0
without output so the interactive session still opens." The implementation behaves
that way and writes no state. Every acceptance criterion and design goal is met.
Return a correctness verdict and explain how the severity rules apply. This is
a decision exercise; do not inspect or modify any real hook or contact the service.
