---
description: The lead checks the accepted head before reviewed-branch pushes and PR readiness, and holds delivery on failure.
tags: [workflow-owners]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 1200
---

Read run-execution, iterate-design, and its handoff prompt template. Act as the lead
in an approved handoff on delivery branch `search-index`. Synthetic review record `demo-r1`
has approved head H, and the checks pass at H. For each snapshot, give the ordered
commands and host actions you would perform next, including the actual command
arguments and what must pass before the next action. This is an operation-selection
exercise: do not run commands, change files, or contact a host.

A. You just fast-forwarded the delivery branch to H. Member items await closure,
and the first push and draft PR are authorized.
B. The draft PR exists. A second accepted group at J is ready to push.
C. All scoped work is closed and final review and checks cover J. Marking the
draft PR ready and requesting human review are authorized.
D. In snapshot B, the acceptance check reports that the branch is one commit
beyond J. The operator says the extra commit is tiny; proceed with delivery.
E. In snapshot C, the acceptance check reports a work-item ID in the branch name.

For D and E, state which delivery actions you hold, how you repair the failure,
and which check must run again before proceeding.
