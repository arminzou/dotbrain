---
name: enter-main-agent
description: Enter the optional two-agent execution protocol from the repo's main checkout on `main`. Use when the user explicitly wants this session to stay in the review/merge station, inspect beads state, optionally dispatch a chosen ready bead into a worker worktree, then review and land the result.
---

# Enter Main Agent

User-triggered only. Use this from the repo's main checkout on `main`, not from a worker
worktree or side branch.

This skill is **coordination only**.

- It declares this session to be the **main agent**.
- It keeps feature implementation out of the main checkout.
- It dispatches a worker only after the execution decision has already been made.
- It reviews, lands, cleans up, and closes completed work.

It does **not** decide the execution graph, ready frontier, or worktree-isolation policy. Those
belong to `operate-execution` (the current implementation of the agreed `operate-execution` role).

## Model

- **Main agent**: stays in the main checkout on `main`, acts as review/merge station, and provides
  a second pair of eyes for the user.
- **Worker agent**: works inside a separate worktree on a branch named
  `<bead-id>-<short-slug>`, implements the slice, makes discoveries, and may use brain skills and
  beads as needed while staying off `main`.

This mode is optional. If the user never chooses worktree parallelism, the session may remain in
main-agent mode without cutting any worktree.

One slice per worktree. One branch per slice.

## Entry

1. Verify that the session is in the repo's main checkout on `main`.

```bash
git branch --show-current
git worktree list
pwd
```

2. Declare main-agent mode and stay in role until explicit exit.

Main-checkout edits are allowed only when they are inherently main-agent work:

- review
- landing
- cleanup
- bead/protocol/doc updates

Feature implementation belongs in a worker session or a separate ordinary single-agent session
outside this mode.

3. Inspect execution state immediately.

```bash
bd ready
bd list --status=in_progress
bd blocked
```

## Dispatch a worker

Use this only after `operate-execution` has already:

- chosen the ready bead
- recommended worktree execution
- recorded enough handoff context for autonomous work

Choose the worker surface:

- Claude Code: `claude --worktree <bead-id>-<short-slug>`
- Codex: `dotbrain codex --worktree <bead-id>-<short-slug>`

Ensure the worktree exists or let the launcher create or reuse it. All worktrees must reach the
same `.brain`, `.beads`, `.claude`, and `.codex` symlinks as the main checkout. Never copy the
Brain or agent workspaces. All worktrees share the same Brainspace `.beads` symlink, so beads state is
live and shared across sessions.

Before handoff, claim or update the bead as needed and emit a concrete worker brief that includes:

- bead ID
- anchor epic, if relevant
- branch/worktree name
- concrete worktree path
- worker agent type
- intended scope
- required checks, if any
- landing or review expectations

Then stop. The worker owns implementation.

## Landing

Re-enter landing flow only after the worker has produced committed work in the existing worktree.

1. Confirm the branch and worktree to land.
2. Review before landing.

```bash
git -C <repo> diff main..<slice>
```

3. Land through the appropriate path:

- PR merge: push, open a PR, wait for CI, merge on the hosting platform.
- Local merge plus branch CI: push the branch for CI, then fast-forward from the main checkout.
- Pure local merge: fast-forward from the main checkout with no push.

```bash
git -C <repo> merge --ff-only <slice>
```

4. Clean up and close completed work.

```bash
git -C <repo> worktree remove <worktree-path>
git -C <repo> branch -d <slice>
bd close <id>
```

Use `bd dolt push` only when the active workflow actually wants sync.

## Exit

Leave main-agent mode only when the user explicitly says to exit it, or when the user starts a
separate ordinary single-agent session outside this protocol.

## Guardrails

- Do not enter this skill from a worker worktree or non-`main` branch.
- Do not do feature work in the main checkout while this mode is active.
- Do not absorb execution-graph policy that belongs to `operate-execution`.
- Do not run broad cleanup from inside an unrelated slice.
- Do not delete another agent's worktree.
- If the branch cannot fast-forward, resolve from the worktree before landing.
