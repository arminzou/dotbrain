# Claude Code worker mechanisms

Use this reference with the shared contract in [Run Execution](../SKILL.md), before worker
preparation or dispatch and before fix rounds, cancellation, or recovery.

## Prepare and dispatch

Dispatch the packaged worker as `dotbrain:worker`; read-only packaged roles are
`dotbrain:reviewer`, `dotbrain:verifier`, and `dotbrain:researcher`. For the explorer role,
use Claude Code's built-in `Explore` agent. The worker's definition always launches it in the
background. For in-place work, dispatch it without isolation. For isolated work, which every
concurrent writer needs, set worktree isolation on the `Agent` call; its definition never sets
isolation, so the lead chooses per dispatch. Do not pass a `name` on a worker's `Agent` call: with
agent teams enabled, a named dispatch without call-level isolation launches as a teammate in the
lead's working directory instead. Address the worker by its agent ID.

Packaged subagents inherit the lead session's permission mode, and their permission prompts surface
in the lead's session. In an unattended run nobody answers them, so the session must already allow
the `git` and `bd` commands its workers and reviewers run.

The launch returns the agent ID at once, and the worker's checkout is
`.claude/worktrees/agent-<agent-id>` in the lead's checkout. Use the actual returned path when
available. Record dispatch while the worker is still starting, before waiting for completion.
Workers discover the shared tracker through Git metadata without wiring their subagent worktrees;
their assignments carry absolute authority references.

Before the first dispatch, when `git check-ignore -q .claude/worktrees/` fails, add
`/.claude/worktrees/` to `$(git rev-parse --git-common-dir)/info/exclude`, so the lead never stages
a worker's worktree. The isolation guard refuses Git commands it cannot attribute to the worker's
worktree, including chained commands and commands a shell hook rewrites. It inspects Bash command
text only; PowerShell commands get just the working-directory check. Tell workers to run Git
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
