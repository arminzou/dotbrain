# Codex worker mechanisms

Use this reference with the shared contract in [Run Execution](../SKILL.md), before worker
preparation or dispatch and before fix rounds, cancellation, or recovery. The path below uses
separate `codex exec` CLI sessions. Native subagent conversations do not establish separate
writing worktrees; do not treat an assigned shell directory as worktree isolation.

## Explorer role

For the read-only explorer role, use Codex's built-in `explorer` agent. If that role is
unavailable, explore in the lead or use a subagent under the session's read-only permissions.
Do not assume a child's requested sandbox overrides broader parent permissions.

## Prepare

The lead creates one detached checkout per writing worker at the assigned base:
`git worktree add --detach <worktree> <base>`, then `dotbrain wire --repo <worktree>`.
Verify that the checkout attaches to the existing Brainspace, delivers the required project
skills and Codex agent files, and does not seed shared conventions or synchronize the tracker.
Leave it detached: the worker creates its item branch once during readiness. Replacements use
the retained item branch and checkout instead.

## Launch

Read the relevant subcommand help only when an option is unknown or rejected. Launch in the background:

```text
codex exec --cd <worktree> --sandbox danger-full-access -c model_reasoning_effort=medium --json -o <final-response-file> -
```

Use the permission policy authorized for this execution; the example is the explicitly authorized
full-access path, not permission to broaden another execution's policy. Worktrees isolate edits,
not filesystem permissions. Supply the bounded assignment through stdin or a file and reuse
configured authentication. Keep stdout JSONL, stderr diagnostics and the final response separate.
On Windows use `pwsh -NoProfile`; background helpers started through `Start-Process` must be hidden.

A separate CLI writer reads the packaged worker definition as instructions; that does not apply
its TOML settings. Set `model_reasoning_effort=medium` explicitly on launch and resume. Inherit the
configured model unless the user explicitly requests a different model. Only for that request,
pass the same `--model <model>` on launch and resume. Confirm model and effort from the session's
recorded turn context.

When the item needs a skill, name it in the assignment by its exact name (`$<skill-name>`) and
require the worker to read it from its assigned worktree before working. A worker told only to
use the project's skills can report having no skill catalog even when the runtime injected one,
and stop before claiming.

Retain the process handle/PID and the session ID from `thread.started`, plus paths to events,
diagnostics, final response and exit evidence. Record dispatch before waiting, with the process
identity if the session ID has not arrived yet. When `thread.started` arrives, add the session ID
to the worker's `work` entry in `dotbrain_artifacts`, where a fix round or takeover finds it.
Do not use an ephemeral session when same-session resume is required.

## Collect and fix

Wait on the retained process handle. Check process exit, session ID from `thread.started`,
turn outcomes (`turn.completed`, `turn.failed`), and error events by event type in the JSONL.
Confirm nested-process termination and required artifacts from their recorded identities and sources.
Read the final response file as the worker's report. Read transcript prose and tool output only
when diagnosing a failure revealed by these signals. A zero exit is process evidence only;
acceptance follows the shared contract.

When the installed CLI supports it, continue a stopped session with
`codex exec resume -c model_reasoning_effort=medium <session-id> -` and the fix assignment through stdin. Run from the original
worktree, reapply the authorized permission policy using supported flags/configuration, and
verify the resumed session ID, actual checkout, branch and claim. Do not use `--last`, which can
select another worker's session, or `--worktree`, which creates a different checkout. Keep the
original assignment and reference paths available. If resume is unavailable, report that fact
and use the shared replacement rules in the same retained worktree after confirmed termination.

## Stop and recover

Stop new dispatch and integration, then request a cooperative stop where an active worker has
an established stop channel; otherwise interrupt its retained process. Account for shell
children and any nested writing agents before declaring termination. On Windows, retain process
creation identities and inspect the descendant tree: a shell-wrapper exit is not proof that its
Codex child or tools stopped. Use process-tree control when required and verify no recorded writer
remains. If termination is uncertain, apply the shared uncertain-termination rule.

A nested writer can outlive its outer worker. A nested `codex exec` started by the worker
through `Start-Process` was already outside the worker's process tree, and stopping the
worker's handle left it running and writing. Before cancelling, record every nested writer's
PID and creation time; the worker must report them. Stop each recorded identity's tree, then
confirm that no recorded identity remains and that its activity and tracker writes have stopped.
Move the claim only after that. A quiet window and an empty worker tree do not establish
termination: a writer with no recorded identity kept writing after both checks passed. Keep its
claim, report the uncertainty and wait for the human decision. Beads refuses an unforced
reassign of a live claim.

Qualified on Windows with Codex CLI 0.161.0 and embedded Beads 1.3.1 for nested writers that
the worker starts as separate processes. Not qualified: native subagent writers, cooperative
stop of a nested writer, claim lease expiry, server-mode trackers, and resumed implementation
after cancellation.

Retain dirty files, untracked files, branches, worktrees and available evidence. Treat a failed
process under the shared failure and attempt rules; it is not a reason to reset or clean up. On
authorized recovery, reconcile the actual tracker and artifacts before replacing or resuming a
worker; use the same checkout without creating its branch again.

## Nested agents

For a bounded native subagent job, set `fork_turns: "none"` when the spawn tool exposes it and
provide the complete assignment. Use bounded history only when the job depends on a named prior
exchange; full history is not the default assignment strategy. If no history control is exposed,
send only the compact assignment and report that inherited context could not be bounded. A fresh
assignment must retain project rules, acceptance criteria, scope, and permission boundaries.
Omit the spawn tool's model option unless the user explicitly requests a different model;
the custom role file supplies effort.
Keep fix rounds in the same worker or reviewer session with findings and the changed diff.

If an assignment requires a custom agent, verify its availability by actually spawning that role
in this CLI session. A delivered TOML file is insufficient. Count nested writing agents toward
the shared writing-worker cap and track their termination; avoid nested writers when direct CLI
workers cover the assignment. Packaged subagents are spawned as `dotbrain-<role>`, for example
a nested reviewer as `dotbrain-reviewer`, and follow the shared item-review rules. A `codex exec`
writer cannot select an agent, so its assignment points it to the packaged worker's definition,
`.codex/agents/dotbrain-worker.toml` in its checkout. Record
direct execution and nested spawning separately; evidence for one does not qualify the other.

## Pre-push notification

If a handoff blocks before its first push, report `BLOCKED` in the current session, naming the
blocker and required human action. No supported agent-invocable runtime-native notification
channel was identified in Codex CLI 0.161.0 or the inspected Windows app surface
(OpenAI.Codex 26.930.7945.0).

Codex supports user-configured turn-completion notifications: `notify` invokes an external
program, TUI notifications emit terminal alerts, and desktop settings control completion and
input alerts. These do not establish a lead-invoked notification tool or guaranteed human receipt.
Do not treat a completion hook as qualified pre-push delivery.

The official [advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[desktop settings](https://learn.chatgpt.com/docs/reference/settings), and
[notifications](https://learn.chatgpt.com/docs/notifications) pages were checked on 2026-10-08.

## Researcher availability

Spawn the packaged researcher as `dotbrain-researcher`. It uses shell tools to read, list,
and search local Brain and codebase files, and dedicated web tools for outside sources.
Its prompt forbids writes, shell networking, installs, permission escalation, credential reads,
and nested delegation. It requests high effort and a read-only sandbox. Web access depends on
dedicated web tools exposed by the parent runtime; report missing web capability when none exists.
If local reads are denied, it reports the missing context instead of bypassing restrictions.

These are behavior rules under the parent's effective permissions, not a guaranteed tool
allowlist or independently enforced read-only boundary. In native Windows CLI 0.160.1 probes,
a child requesting read-only under a full-access lead could mutate disposable files and open an
outbound TCP connection. A read-only lead blocked reading the challenge script, leaving its
write/network challenges untested. The shell-reading path accepts that parent-policy tradeoff;
do not claim that the custom TOML prevents writes when the lead runs with broader permissions.

Collaboration tools also remained exposed despite `multi_agent = false`. The researcher must
follow its no-delegation instruction. Web-page reads succeeded through the inherited
`mcp__codex_apps__search_service_web_run` connector. Use that dedicated tool when available;
do not substitute shell networking when web tools are absent.

CLI 0.161.0 qualification spawned the packaged researcher under parent `web_search` values
`disabled` and `live`, keeping the child setting `live`. Both exposed the inherited search
connector and no native web tool. Because the parent-live control also lacked native search,
these observations do not isolate whether the child setting was consumed, ignored, or masked.
The unverified child `web_search` override has been removed; it does not qualify independent
native access. The official [custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [web-search documentation](https://learn.chatgpt.com/docs/web-search) were checked on 2026-10-08.

No reader MCP server is required or provisioned. An earlier no-shell probe could combine private
context and web sources using a local read-only MCP reader registered in the parent session,
but the packaged researcher uses shell reads instead. Claude Code retains its native file-read
tool allowlist and has no shell access.

The [official custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
explains configuration inheritance and the parent live permission overrides. Verify the
effective permissions in the actual launch rather than relying on file defaults alone.
