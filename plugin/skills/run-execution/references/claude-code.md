# Claude Code worker mechanisms

Use this reference with the shared contract in [Run Execution](../SKILL.md), before worker
preparation or dispatch and before fix rounds, cancellation, or recovery.

Apply [capacity and isolation](parallel-execution.md#capacity-and-isolation).
This reference supplies the runtime mechanisms only.

## Prepare and dispatch

Apply [role dispatch](../SKILL.md#role-dispatch). Packaged roles are `dotbrain-worker` and the
read-only `dotbrain-reviewer`, `dotbrain-verifier`, and `dotbrain-researcher`, available when the
checkout's `.claude/agents/` has them. Otherwise set `subagent_type: general-purpose` and put the
role contract at the top of the `Agent` prompt. For the explorer role, use Claude Code's built-in
`Explore` agent. Dispatch roles by agent type, never as a fork of the lead's conversation. Always
launch a worker in the background: the packaged definition does so itself; for a generic worker,
set `run_in_background` on the `Agent` call. For in-place work, dispatch it without isolation.
For isolated work, set worktree isolation on the `Agent` call; no definition sets isolation, so
the lead chooses per dispatch. Do not pass a `name` on a worker's `Agent` call: with
agent teams enabled, a named dispatch without call-level isolation launches as a teammate in the
lead's working directory instead. Address the worker by its agent ID.

Send the self-contained assignment in the `Agent` prompt, with exact source sections and checks,
without pasting the lead's conversation or dispatch, integration, and recovery references.
Omit the call's `model` option unless the user explicitly requests a different model;
otherwise inherit the configured model.
A packaged definition supplies role effort; a generic subagent inherits the session's. Retain the original agent ID for fix rounds instead of
repeating startup and discovery in a replacement session.

Subagents inherit the lead session's permission mode, and their permission prompts surface
in the lead's session. In an unattended run nobody answers them, so the session must already allow
the `git` and `bd` commands its workers and reviewers run.

Dispatch a reviewer without isolation, pointed at the detached review worktree the lead created.

The launch returns the agent ID at once; record it in `Dispatched` as an in-session subagent.
The worker's checkout is `.claude/worktrees/agent-<agent-id>` in the lead's checkout. Use the actual returned path when
available. Record dispatch while the worker is still starting, before waiting for completion.
Workers discover the shared tracker through Git metadata without wiring their subagent worktrees;
their assignments carry precise source sections and references.

Before the first dispatch, when `git check-ignore -q .claude/worktrees/` fails, add
`/.claude/worktrees/` to `$(git rev-parse --git-common-dir)/info/exclude`, so the lead never stages
a worker's worktree. The isolation guard refuses Git commands it cannot attribute to the worker's
worktree, including chained commands and commands a shell hook rewrites. It inspects Bash command
text only. On Claude Code 2.1.293 on Windows, the PowerShell tool is not guarded: Git aimed at the
main checkout through it (`git -C`, `GIT_DIR`, `Set-Location`, a nested `pwsh`) runs and commits,
where the same commands through Bash are refused. Tell workers to run Git through the Bash tool
where it exists, since only Bash is guarded; where PowerShell is the only shell, to run Git only
inside their own worktree, never with `-C`, `GIT_DIR`, or a location outside it. Either way, run
Git as plain, separate commands and set commit identity through the `GIT_AUTHOR_*` and
`GIT_COMMITTER_*` environment variables.

## Collect and fix

Apply the shared [completion handling](execution-record.md#completion-handling) rules when processing
available results. A native completion notification does not establish item acceptance.

Collect the native task completion notification and the worker's candidate and check evidence.
Retain the agent ID for follow-up. A completed task can resume with `SendMessage` to that original
ID in the lead session that spawned it; use this for item-review fixes and conflict rebases.
The resumed worker continues in its original worktree.

Apply [capacity rules](parallel-execution.md#capacity-and-isolation)
before refilling or resuming a writer. This does not qualify higher-fan-out isolation.

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

## Claude Code workers for another runtime's lead

The sections above assume a Claude Code lead using the `Agent` tool. A lead in another runtime
launches Claude Code workers as separate `claude -p` sessions instead. Prepare a worktree as the
lead's own reference does, and wire it with `dotbrain wire --repo <worktree>` so the plugin and
project resources resolve. Launch in the background from that worktree with the assignment on
stdin, `--agent dotbrain-worker` (without it, the worker role contract heads the stdin
assignment), `--output-format json`, and full access
(`--permission-mode bypassPermissions`); nobody answers prompts in an unattended run. Generate the worker's ID up front and
pass it as `--session-id <uuid>`, so `Dispatched` records it as a CLI session before launch; the JSON result
carries the same `session_id`. Resume fix rounds with `claude -p --resume <session-id>`, adding the
same `--agent` option, from the same worktree, passing `--permission-mode bypassPermissions` again, since a
resume starts in the default mode; the worker keeps its earlier turns. Stop a worker by
ending its process tree. Check `claude --help` when an option is rejected.

Qualified on Windows with Claude Code 2.1.301, launched from a shell rather than a running Codex
lead, for dispatch, commit in a plain Git worktree, and a resumed fix round. Not qualified:
cancellation, and a worktree wired by `dotbrain wire`.
