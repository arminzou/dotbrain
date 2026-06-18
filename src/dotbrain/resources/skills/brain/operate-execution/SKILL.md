---
name: operate-execution
description: Operate the private execution engine for a project control root. Use when the user wants to shape work, inspect ready work, claim/update/close work items, split or discover follow-up work, or connect private execution to public issues.
---

# Operate Execution

Operate the control root's private execution layer: a typed, prioritized **dependency graph** of
work items. The engine is declared in `project.yaml` (`execution-engine:`, today beads). This skill
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

1. **`.brain/agents/issue-tracker.md`** — project conventions shared with `triage-public`: linking
   rules, ADR policy, priority deviations. Lives in the Brain. Empty means pure defaults.
2. **[references/beads.md](references/beads.md)** — engine mechanics and native-modeling rules:
   commands, types, dependencies, status, labels. Swap for the active engine's reference if it changes.

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

## Execution-mode recommendation

When a ready item is under consideration, recommend one of:

- **Current session** — small, local, low-contention work.
- **Worktree** — substantial work, likely discoveries, Brain-plus-code changes, or isolated review.

Advisory, not a gate; always include a one-line reason. **Stop after the recommendation** — do not
claim, branch, or implement until the user responds. A prior green light covers the agreed step
only; still pause before expanding scope or starting the next.

## Operating loop

1. Read the context files above, then project Brain context and relevant ADRs.
2. Inspect the graph: ready frontier, list, and item detail (commands in `references/beads.md`).
3. Decide what the work needs: new items, a re-slice, dependency changes, or only status updates.
   Prefer thin, independently verifiable slices; use real dependencies for blockers, not prose.
4. Recommend the next ready item and its execution mode, then stop for sign-off.
5. If work proceeds, claim or update the item and record context another agent would otherwise lose.
6. If discoveries change reality, update the graph instead of forcing stale plans to stand.
7. Close items explicitly when their acceptance criteria are actually satisfied.

## Discoveries and re-slicing

When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
directly; create or update related items when new work becomes explicit; split or re-slice the
current item when it is no longer the right shape; adjust dependencies or acceptance when the graph
is wrong. Put discoveries back into the graph, never into ad hoc todo files.

## Handoff context

When recommending worktree execution or handing work off, record enough that the worker can act
without being spoon-fed: work-item ID, anchor epic (if any), branch/worktree name, intended scope,
required checks, and review/landing expectations. Agent-created branches use the canonical name
`<item-id>-<short-slug>` (the bead ID for beads), which supports SessionStart anchor inference.

## Public/private link

Public issues and private items are linked, not field-synced: pull an issue inward by creating a
private item that references it; publish outward by deriving a public-safe issue and recording its
reference on the item. A PR's `Closes #N` closes the public issue only — the private item still
needs an explicit close. Mechanics live in [references/beads.md](references/beads.md).

## Pitfalls

- **Do not jump from recommendation to execution.** Stop and wait for confirmation — the most common
  failure mode.
- **Check for existing branches first.** Run `git branch -a | grep -i <topic>`; if one exists, ask
  whether to use it or start fresh.
- **Do not close an item without presenting what was done.** Summarize and confirm first, unless the
  user explicitly asked you to close it.
