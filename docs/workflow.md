# Choose your engineering workflow

Dotbrain preserves project understanding and durable work state. Its five core
skills provide wiring, context maintenance, repository requirements, and native
Beads operations. Your selected engineering workflow decides how to investigate,
plan, delegate, verify, recover, and deliver work under user and repository authority.
Core-only projects work without pstack.

```mermaid
flowchart TB
  accTitle: A selected workflow uses independent Dotbrain capabilities
  workflow["`**Selected workflow**
  planning and delivery`"]
  brain["`**Brain**
  context and evidence`"]
  graph["`**Beads**
  tasks and ownership`"]
  rules["`***RULES.md***
  adopted requirements`"]
  workflow -- reads and maintains --> brain
  workflow -- records work in --> graph
  workflow -- follows --> rules
```

Use `maintain-brain` to capture vocabulary, accepted decisions, designs, verified
findings, and unresolved hypotheses with their evidence. Use `work-graph` for
tasks, dependencies, claims, and execution evidence. Ask `repo-rules` explicitly
to initialize repository requirements; its assessment alone adopts no policy.
Enforcement implementation belongs to your engineering workflow.

## Optional pstack integration {#pstack}

Dotbrain maintains a project-local `dotbrain-pstack` mode that adapts external
[pstack](https://github.com/backnotprop/pstack) capabilities to the Brain and Beads.
It is a separate CLI-delivered resource, outside the five-skill marketplace core.
Wiring a project does not opt it in, install pstack, or select a general workflow
for core-only projects.

### Prepare the dependency {#dependency}

Keep a separate, clean checkout of the pinned source:

```bash
git clone https://github.com/backnotprop/pstack.git ~/pstack
git -C ~/pstack checkout 9cd6939b766cb920f1c44970d7c7ee1ec28bd0d6
```

This integration expects manifest version `0.15.36` at that exact revision.
Dotbrain checks the source root, revision, clean Git state, manifest, and complete
tracked resource files. Keep this checkout unchanged, including untracked files.
`wire`, `refresh`, and `doctor` never fetch, install, or update the dependency.
Another revision or installation form needs separate qualification.

### Opt in for a project {#opt-in}

Edit the existing project declaration, preserving unrelated settings:

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
pstack:
  enabled: true
  source: ~/pstack
```

`enabled` is a YAML boolean, defaulting to `false`. `source` must be an absolute
path or start with `~/`; relative paths are rejected. Opt-in requires an initialized,
reachable Beads backend (`beads.mode: embedded` or `server`). See
[configuration](configuration.md#pstack) and [Beads setup](beads-backend.md).

From each wired checkout, reconcile delivery and inspect the result:

```bash
dotbrain refresh
dotbrain doctor
```

Use `dotbrain refresh --all` for registered projects. Configured Claude Code and
Codex workspaces receive `.claude/skills/dotbrain-pstack/` and
`.agents/skills/dotbrain-pstack/`. These links point to a separate owned integration
cache in the private home. The ignored `.dotbrain-pstack.json` records dependency
selection and delivered locations; edit the declaration, not this generated record.
Startup adds a bounded discovery pointer rather than the workflow's instructions.
Restart sessions after changing the selection, then use the runtime's displayed
`dotbrain-pstack` skill for engineering work.

The mode coordinates task selection, coordinator-owned claims, local worktree
delegation, independent verification, context capture, and recovery. It calls the
adapted external capabilities rather than also running pstack's top-level
`poteto-mode`. Scope, acceptance criteria, permissions and delivery authority
still come from the user and repository. Opt-in grants no publication, messaging,
merge, deployment, or release permission.

### Qualification scope {#qualification}

The initial native qualification targets are local Windows Claude Code `2.1.325`,
Codex `0.169.0`, and Beads `1.3.1`, with the pinned pstack source above.
Qualification must retain the exact integrated Dotbrain revision, runtime and
dependency versions, settings, and independently inspectable traces. Consult the
release or PR verification evidence for observed results at that revision.

Source checks and delivered files establish identity and filesystem state.
Native runs are needed to establish discovery and use, Beads ownership and
closure, cross-session retrieval, and interruption/recovery behavior. A healthy
doctor report alone proves none of those agent outcomes. Other operating systems,
runtimes, dependency revisions, and cloud workers are outside this initial mode
qualification scope. The six core runtime integrations retain their separate
[installation and limitations](getting-started.md).

### Opt out or upgrade {#opt-out}

Set `pstack.enabled: false` and refresh each affected checkout. Dotbrain removes
only attributable, intact mode links and its discovery record; modified or foreign
resources are preserved and reported. Inspect those resources explicitly before
starting another session. External pstack sources and foreign installations stay
with their owner. Start a fresh session after opt-out.

Keep the qualified dependency pinned during ordinary updates. A pstack upgrade
requires reviewing referenced capabilities and adaptations and repeating affected
qualification; changing a version string is insufficient. For the core breaking
transition, active-work safety, backups, and rollback, read [Upgrading](upgrading.md).
