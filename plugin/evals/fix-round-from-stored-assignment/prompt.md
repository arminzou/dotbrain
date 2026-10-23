---
description: A review-fix round resumes the original worker with the consolidated assignment rebuilt from the item's records, the findings by reference, and the delta.
tags: [dispatch-records]
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Read run-execution and its execution record. You are the lead that dispatched this worker,
in this same session, but your context was compacted: you know its assignment only from
these records on item alpha. Decide the next operations; do not mutate
files, run tracker commands, or dispatch agents.

```text
## Dispatched: worker-a in /work/alpha on page-orders @ 1a2b3c4
Runtime: Claude Code, in-session subagent, agent ID a77. Assignment as sent:
**Item:** alpha · implement · actor worker-a
**Checkout:** /work/alpha on page-orders @ 1a2b3c4
**Change:** Paginate GET /orders with a cursor.
**Ownership:** src/orders.py · order listing · overlap: none
**Acceptance:** Responses hold at most 50 orders and a next cursor.
**Checks:** make test
**Limits:** role default
**Constraints:** Keep the response field names unchanged.
**Overrides:** none
**Sources:** docs/api.md#orders

## Candidate @ 5d6e7f8
**Status:** DONE · **Observed:** 5d6e7f8

## Review 1: CHANGES @ 5d6e7f8 (round 0)
F1 high src/orders.py:40 The cursor skips the 50th order.
```

Since the review, the human settled one more constraint: the cursor must be opaque.
Write the exact fix-round record you append and the exact message you send, and say
which worker receives it and when a different worker could.
