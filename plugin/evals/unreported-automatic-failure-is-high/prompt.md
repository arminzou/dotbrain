---
description: The reviewer rates unreported automatic failure high even when later calls remain usable.
tags: [goal-shortfalls, state]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Use the packaged reviewer definition to review automatic-refresh against main.
This is a direct code review, with no tracker writes. The design requires automatic
refresh to report failure and remain usable on later runs; it accepts no silent-failure
mode. Trace an OSError from fetch. Later calls can succeed and no state is left behind.
Return severity and verdict. Do not repair the code. Judge the failure even if the
happy-path acceptance tests pass; do not widen this into a final branch-goal review.
