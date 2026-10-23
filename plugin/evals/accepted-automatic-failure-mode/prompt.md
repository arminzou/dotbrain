---
description: The automatic-failure default respects a failure mode explicitly accepted by the design.
tags: [goal-shortfalls]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read run-execution's review verdict rules and review-gate's final review rules.
Consider a change to a session-start diagnostic hook: the approved design explicitly
accepts silent fail-open when the external service is unavailable, so the interactive
session still opens. The implementation does exactly that and leaves no state blocking
later attempts. There is no unmet goal or acceptance criterion and no other defect.
Return a correctness verdict and explain how the severity default applies. This is
a decision exercise; do not inspect or modify any real hook or contact the service.
