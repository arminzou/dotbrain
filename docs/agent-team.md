# Work with an agent team

Your engineering workflow and agent runtime own delegation. Dotbrain provides the
shared Brain, native Beads access, and delivery of your selected custom agents.
The five-skill core ships no worker, reviewer, verifier, or researcher definitions.

## Shared context and work state

Wired Git worktrees share the project's Brain and Beads store while keeping their
runtime resource delivery local to each checkout. `maintain-brain` supplies record
operations; `work-graph` supplies native graph and ownership operations. A task's
dependency eligibility is separate from authorization, writer capacity, and acceptance.

The chosen workflow decides what delegates receive, who writes each resource,
which checks establish acceptance, and how interrupted work resumes. Preserve
actual candidates, claims, evidence and remaining limits at handoff. Concurrent
writers must reconcile current content before saving shared records.

## Custom agents {#the-packaged-subagents}

Use `subagents:` in global `config.yaml` or project `project.yaml` to select your
own Claude Code or Codex definitions. Sources live under
`~/dotbrain/subagents/claude/` and `~/dotbrain/subagents/codex/`.
The `dotbrain-` prefix remains reserved to protect preserved old resources.

```bash
dotbrain subagents list
dotbrain subagents link
dotbrain subagents link --scope global
```

Claude definitions are linked. Codex definitions are generated TOML copies with
the `# dotbrain-managed-agent: v1` marker. Edit sources rather than generated
resources. Modified or foreign resources and collisions need explicit inspection;
see [configuration](configuration.md#global-subagents) and
[session context](session-context.md#subagents).

Filesystem delivery does not prove that a runtime loaded or spawned an agent.
Hermes, OpenCode, Pi and Cursor receive core skills and session integrations,
but Dotbrain does not deliver native custom subagents to them.

## Optional pstack mode

The selected `dotbrain-pstack` mode uses local native general agents and wired
isolated worktrees for writing delegates. Its coordinator owns task claims,
records worker identities and candidate revisions, arranges verification, and
closes accepted work. Workers return evidence within their assignments.
Recovery requires reconciling work and writer authority; silence alone does not
establish that a writer stopped. These procedures belong to the mode rather than
the core or a packaged agent role.

Read [setup and qualification scope](workflow.md#pstack) before selecting the mode.
Native qualification evidence is required for delegation, ownership and recovery
claims at a named revision. Mode selection never expands user or repository authority.
