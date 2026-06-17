---
name: operate-beads
description: Operate the private beads execution graph for a project control root. Use when the user wants to shape work, inspect ready work, claim/update/close beads, split or discover follow-up work, or connect private execution to public issues.
---

# Operate Beads

Operate the control root's private execution layer through beads (`bd`).

The beads dependency graph is the concurrency contract: what is `bd ready`
(unblocked) is the set safe to run in parallel across workers; blocked edges
are the serialization. There is no separate coordination mechanism.

- **Public issue tracker**: handled by `triage-public`.
- **Private execution graph**: beads issues in the control root's `.beads/`.
- **Knowledge layer**: `.brain/CONTEXT.md`, `.brain/adr/`, and `.brain/AGENTS.md`; written by their
  owning skills.

Beads is the source of truth for private execution. Do not recreate task state in markdown docs.
Use `bd prime` for the version-current command reference. See
[references/operating-beads.md](references/operating-beads.md) for the native modeling rules.

## What this skill owns

This skill owns the **beads execution graph**:

- shape epics, tasks, dependencies, and acceptance criteria
- choose the ready frontier
- recommend an execution mode for ready work
- record handoff context that lets another agent work autonomously
- link private execution to public issues
- absorb discoveries back into the graph when work reveals new reality

It does **not** perform worktree implementation. That coordination belongs to `enter-main-agent`.

## Who uses it

Both **main-agent** and **worker-agent** sessions may use this skill.

- The main agent uses it to shape work, inspect readiness, recommend execution mode, and maintain
  the overall graph.
- A worker agent may use it while advancing its assigned area: claim, update, split, create, and
  close related beads as discoveries emerge.

Worker autonomy is intentional. The boundary is soft: stay anchored to the bead or epic the user or
main agent asked you to work on, but do not freeze when the work reveals missing scope.

## Execution-mode recommendation

When multiple ready items exist, recommend the smallest useful continuation first.

When a ready item is under consideration, recommend one of:

- **Current session**: for small, local, low-contention work.
- **Worktree**: for substantial work, likely discoveries, Brain-plus-code changes, or isolated
  review.

The recommendation is advisory, not a gate. Always include a one-line reason.

**Important: stop after the recommendation.** Do not proceed to claim, update, branch, or
implement until the user responds. A recommendation is not an implicit go-ahead — execution
requires user sign-off. If you've been given a prior green light (e.g. "go ahead" or "ok go"),
that covers the already-agreed step only — still pause before expanding scope or starting the
next step.

## Basic operating loop

1. Read project Brain context and relevant ADRs.
2. Inspect the current graph with `bd ready`, `bd list`, and `bd show`.
3. Decide whether the work needs new beads, a re-slice, dependency changes, or only status updates.
4. Recommend the next ready item and its execution mode.
5. If work proceeds, claim or update the relevant bead and record any context another agent would
   otherwise lose.
6. If discoveries change reality, update the graph instead of forcing stale plans to stand.
7. Close beads explicitly when their acceptance criteria are actually satisfied.

## Commands

Run from the repo root or control root. Use `bd -C <repo-or-control-root> ...` when current
directory is elsewhere.

```bash
bd ready
bd list
bd show <id>
bd create "Title" --type task --description "..."
bd create "Epic title" --type epic
bd create "Child title" --parent <epic-id> --type task
bd dep add <blocked-id> <blocker-id>
bd update <id> --claim
bd update <id> --status in_progress
bd close <id>
bd dolt pull
bd dolt push
```

Prefer thin, independently verifiable slices. Use dependencies for real blockers instead of prose
such as "blocked by task 02."

## Discoveries and re-slicing

When implementation exposes hidden requirements or follow-up work:

- do the obvious in-scope work directly
- create or update related beads when new work becomes explicit
- split the current work when one bead is no longer the right shape
- adjust dependencies or acceptance criteria when the old graph is now wrong

Do not mirror discoveries into ad hoc todo files. Put them back into beads.

## Handoff context

When recommending worktree execution or handing work to another agent, record enough context that
the worker can act without being spoon-fed:

- bead ID
- anchor epic, if relevant
- branch or worktree name
- intended scope
- required checks, if any
- review or landing expectations

For agent-created worktrees, the canonical branch/worktree name is:

```text
<bead-id>-<short-slug>
```

This supports SessionStart anchor inference.

## Public/private link

Public issues and private beads are linked, not field-synced.

- Public issue pulled inward: create a private bead with `--external-ref gh-<number>`.
- Private idea published outward: derive a public issue in public-safe language, then update the
  bead with the public reference.

If a public issue exists, remember that a PR `Closes #N` closes the public issue only. The private
bead still needs explicit `bd close`.

## Labels

Beads work is modeled with native fields: `--type`, `--priority`, status, and dependencies, not a
private label vocabulary. See [references/operating-beads.md](references/operating-beads.md) for
the detailed rules.

Record a label convention in `.brain/agents/labels.md` only when a project actually adopts one:

- a facet vocabulary used in beads, or
- the GitHub-label-to-native mapping that `triage-public` applies

An absent file means no project label convention and pure native fields.

## Pitfalls

- **Do not jump from recommendation to execution.** After step 4 (recommend), stop and wait for
  user confirmation. Skipping this handshake is the most common failure mode — the user expects
  to approve before you touch code.
- **Check for existing branches before starting.** Before implementing any code changes, run
  ``git branch -a | grep -i <topic>`` to see if a branch already exists for the work. If one
  does, ask the user whether to use it or start fresh — do not assume.
- **Do not close a bead without presenting what was done.** After implementation, summarize
  the changes and confirm with the user before closing, unless the user explicitly asked you to
  close it.
