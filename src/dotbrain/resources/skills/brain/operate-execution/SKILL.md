---
name: operate-execution
description: Create, claim, work on, and close issues in the project's private execution graph. Use when filing issues, creating work items, claiming tasks, inspecting the ready frontier, updating work status, or closing completed work — any interaction with the project issue tracker.
---

# Operate Execution

Operate the Brainspace's private execution layer: a typed, prioritized **dependency graph** of
work items. The engine is declared in `project.yaml` (`execution-engine:`). This skill
is engine-agnostic — it owns the model and workflow; the engine's CLI mechanics and native-modeling
rules live in `references/<engine>.md` ([references/beads.md](references/beads.md) for beads).

The dependency graph is the concurrency contract: the **ready frontier** (open items with no open
blockers) is the set safe to claim and run in parallel; blocking edges are the serialization. There
is no separate coordination mechanism.

- **Private execution graph** — work items in the engine's store; this skill owns it and it is the
  source of truth. Never mirror work state into markdown docs, ROADMAPs, or task lists.
- **Public issue tracker** — handled by `triage-public`; linked to private work, not synced.
- **Knowledge layer** — `.brain/CONTEXT.md`, `.brain/adr/`, `.brain/AGENTS.md`; owned by other skills.

## Context files

Read at session start, before inspecting the graph:

1. **`.brain/AGENTS.md`** (Project section) — project tracker conventions shared with
   `triage-public`: linking rules, ADR policy, priority deviations. Absent or empty means pure defaults.
2. **[references/beads.md](references/beads.md)** — engine mechanics and native-modeling rules:
   commands, types, dependencies, status, labels. Swap for the active engine's reference if it changes.
3. **[references/work-intake.md](references/work-intake.md)** — work intake pipeline: when to create a
   issue directly vs when to suggest a PRD + epic. Read to decide how new work enters the graph.

## What this skill owns

- shape epics, tasks, dependencies, and acceptance criteria
- choose the ready frontier and recommend the smallest useful continuation
- recommend an execution mode for ready work (below)
- record handoff context that lets another agent work autonomously
- link private execution to public issues
- absorb discoveries back into the graph when work reveals new reality

It does **not** perform worktree implementation; that coordination belongs to `enter-main-agent`.

## Who uses it

Both **main-agent** and **worker-agent** sessions. The main agent shapes work, inspects readiness,
recommends mode, and maintains the graph. A worker may claim, update, split, create, and close
related items as discoveries emerge. Worker autonomy is intentional: stay anchored to the assigned
item or epic, but do not freeze when work reveals missing scope.

## Human gate

Items flagged for human review need a person's decision before an agent proceeds. The agent
checks for gated items before each new item and treats only flagged items as gated.

Unflagged items are **autonomous**: the agent may pick them up, work them, and close them without
stopping for sign-off. This is the default because most items are small enough that the check-in
adds friction without value. The human-review flag is the intentional exception.

Flag an item for human review when it genuinely needs a decision — scope ambiguity, design
trade-offs, cross-cutting impact, or anything you want to see before work starts. Leave
everything else unflagged so the agent can flow through the ready frontier.

## Execution-mode recommendation

When a human-gated ready item is under consideration, recommend one of:

- **Current session** — small, local, low-contention work.
- **Worktree** — substantial work, likely discoveries, Brain-plus-code changes, or isolated review.
- **Skip** — the item needs a decision you want to make; leave it for later triage.

Advisory, not a gate; always include a one-line reason. Stop after the recommendation and wait for
the user to respond. Skip means the item stays in the human queue.

Autonomous (unflagged) items do not need a mode recommendation — claim and work them directly.

## Operating loop

1. Read the context files above, then project Brain context and relevant ADRs.
2. Inspect the graph: ready frontier, list, and item detail (commands in `references/beads.md`).
3. Check for human-gated items among the ready set (engine reference covers the command).
4. Select the next ready item:
   - **Human-gated** — recommend mode and stop for sign-off before claiming.
   - **Autonomous** — claim directly and proceed.
5. Implement, update notes, and close when acceptance criteria are satisfied.
6. If discoveries change reality, update the graph instead of forcing stale plans to stand.
7. Return to step 2. Continue until the ready frontier is empty or hits a human-gated item
   whose decision you're not present to make.

## Discoveries and re-slicing

When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
directly; create or update related items when new work becomes explicit; split or re-slice the
current item when it is no longer the right shape; adjust dependencies or acceptance when the graph
is wrong. Put discoveries back into the graph, never into ad hoc todo files.

## Handoff context

When recommending worktree execution or handing work off, record enough that the worker can act
without being spoon-fed: work-item ID, anchor epic (if any), branch/worktree name, intended scope,
required checks, and review/landing expectations. Agent-created branches use the canonical name
`<item-id>-<short-slug>` (the issue ID in the configured engine), which supports SessionStart anchor inference.

## Public/private link

Public issues and private items are linked, not field-synced: pull an issue inward by creating a
private item that references it; publish outward by deriving a public-safe issue and recording its
reference on the item. A PR's `Closes #N` closes the public issue only — the private item still
needs an explicit close. Mechanics live in [references/beads.md](references/beads.md).

## Pitfalls

- **Do not jump from recommendation to execution for human-gated items.** Stop and wait for confirmation from the user. Autonomous (unflagged) items flow through without a stop — the gate handles separation.
- **Do not skip the human-gate check at the start of the loop.** Check it every iteration — the set of gated items may change as other items close or as new items are created.
- **Check for existing branches first.** Run `git branch -a | grep -i <topic>`; if one exists, ask
  whether to use it or start fresh.
- **Do not close an item without presenting what was done.** Summarize and confirm first, unless the
  user explicitly asked you to close it.
