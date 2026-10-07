# Claude Code worker mechanisms

Use this reference with the shared contract in [Run Execution](../SKILL.md), before worker
preparation or dispatch and before fix rounds, cancellation, or recovery.

## Prepare and dispatch

Dispatch each concurrent writing worker as a background subagent with worktree isolation on the
`Agent` call, using a role allowed to create a branch and commit, such as `general-purpose`.
The packaged `implementer` is a sole writer sharing the lead's checkout for a small change,
and refuses an item that needs a branch.

The launch returns the agent ID at once, and the worker's checkout is
`.claude/worktrees/agent-<agent-id>` in the lead's checkout. Use the actual returned path when
available. Record dispatch while the worker is still starting, before waiting for completion.
Workers discover the shared tracker through Git metadata without wiring their subagent worktrees;
their assignments carry absolute authority references.

Before the first dispatch, when `git check-ignore -q .claude/worktrees/` fails, add
`/.claude/worktrees/` to `$(git rev-parse --git-common-dir)/info/exclude`, so the lead never stages
a worker's worktree. The isolation guard refuses Git commands it cannot attribute to the worker's
worktree, including chained commands and commands a shell hook rewrites. Tell workers to run Git
as plain, separate commands and set commit identity through the `GIT_AUTHOR_*` and
`GIT_COMMITTER_*` environment variables.

## Collect and fix

Collect the native task completion notification and the worker's candidate and check evidence.
Retain the agent ID for follow-up. A completed task can resume with `SendMessage` to that original
ID in the lead session that spawned it; use this for item-review fixes and conflict rebases.
The resumed worker continues in its original worktree.

## Stop and recover

Ask active workers to stop through `SendMessage`. Retain their acknowledgement and native
completion status; sending a message alone does not prove termination. Apply the shared
uncertain-termination rule if completion cannot be established.

Reconcile the recorded worktree with the filesystem: Claude may automatically remove a clean
subagent worktree after completion. Report a missing artifact rather than assume it survives.
Do not use a new worktree-isolated subagent to take over another worker's worktree: its isolation
guard remains tied to its new checkout. A replacement must use a runtime path that can actually
operate in the retained checkout. A fresh `claude -p --worktree <name>` session can reopen a
Claude-named worktree; other checkout types require separate capability evidence. Preserve the
shared recovery contract and report unsupported paths.
