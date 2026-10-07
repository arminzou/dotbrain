# Codex worker mechanisms

Use this reference with the shared contract in [Run Execution](../SKILL.md), before worker
preparation or dispatch and before fix rounds, cancellation, or recovery. The path below uses
separate `codex exec` CLI sessions. Native subagent conversations do not establish separate
writing worktrees; do not treat an assigned shell directory as worktree isolation.

## Prepare

The lead creates one detached checkout per writing worker at the assigned base:
`git worktree add --detach <worktree> <base>`, then `dotbrain wire --repo <worktree>`.
Verify that the checkout attaches to the existing Brainspace, delivers the required project
skills and Codex agent files, and does not seed shared conventions or synchronize the tracker.
Leave it detached: the worker creates its item branch once during readiness. Replacements use
the retained item branch and checkout instead.

## Launch

Read the installed CLI's help before assembling commands. Launch in the background:

```text
codex exec --cd <worktree> --sandbox danger-full-access --json -o <final-response-file> -
```

Use the permission policy authorized for this execution; the example is the explicitly authorized
full-access path, not permission to broaden another execution's policy. Worktrees isolate edits,
not filesystem permissions. Supply the bounded assignment through stdin or a file and reuse
configured authentication. Keep stdout JSONL, stderr diagnostics and the final response separate.
On Windows use `pwsh -NoProfile`; background helpers started through `Start-Process` must be hidden.

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

Wait on the retained process handle. Record its terminal exit and inspect `turn.completed`,
`turn.failed` and error events together with candidate artifacts and check evidence. A zero exit
is process evidence only; acceptance follows the shared contract.

When the installed CLI supports it, continue a stopped session with
`codex exec resume <session-id>` and the fix assignment through stdin. Run from the original
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

Retain dirty files, untracked files, branches, worktrees and available evidence. Treat a failed
process under the shared failure and attempt rules; it is not a reason to reset or clean up. On
authorized recovery, reconcile the actual tracker and artifacts before replacing or resuming a
worker; use the same checkout without creating its branch again.

## Nested agents

If an assignment requires a custom agent, verify its availability by actually spawning that role
in this CLI session. A delivered TOML file is insufficient. Count nested writing agents toward
the shared writing-worker cap and track their termination; avoid nested writers when direct CLI
workers cover the assignment. Packaged subagents are spawned as `dotbrain-<role>`, for example
a nested reviewer as `dotbrain-reviewer`, and follow the shared item-review rules. A `codex exec`
writer cannot select an agent, so its assignment points it to the packaged worker's definition,
`.codex/agents/dotbrain-worker.toml` in its checkout. Record
direct execution and nested spawning separately; evidence for one does not qualify the other.

## Researcher availability

Spawn the packaged researcher as `dotbrain-researcher`. It uses shell tools to read, list,
and search local Brain and codebase files, and dedicated web tools for outside sources.
Its prompt forbids writes, shell networking, installs, permission escalation, credential reads,
and nested delegation. It requests high effort, live web search, and a read-only sandbox.
If local reads are denied, it reports the missing context instead of bypassing restrictions.

These are behavior rules under the parent's effective permissions, not a guaranteed tool
allowlist or independently enforced read-only boundary. In native Windows CLI 0.160.1 probes,
a child requesting read-only under a full-access lead could mutate disposable files and open an
outbound TCP connection. A read-only lead blocked reading the challenge script, leaving its
write/network challenges untested. The shell-reading path accepts that parent-policy tradeoff;
do not claim that the custom TOML prevents writes when the lead runs with broader permissions.

Collaboration tools also remained exposed despite `multi_agent = false`. The researcher must
follow its no-delegation instruction. Web-page reads succeeded through an inherited connector;
that does not separately establish the effect of the native `web_search` setting.

No reader MCP server is required or provisioned. An earlier no-shell probe could combine private
context and web sources using a local read-only MCP reader registered in the parent session,
but the packaged researcher uses shell reads instead. Claude Code retains its native file-read
tool allowlist and has no shell access.

The [official custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
explains configuration inheritance and the parent live permission overrides. Verify the
effective permissions in the actual launch rather than relying on file defaults alone.
