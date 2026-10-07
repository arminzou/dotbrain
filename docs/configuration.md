# Configuration

Most setups never edit configuration. When you do, there are four files, all in your private
dotbrain home:

```mermaid
treeView-beta
  accTitle: Where dotbrain's configuration files live
  ~/dotbrain/
    config.yaml ## machine: shared infrastructure
    skills/
      skills.yaml ## machine: global skills
    agents/
      agents.yaml ## machine: global subagents
    brainspaces/
      my-app/
        .brain/
          project.yaml ## one project
```

| File | Scope | Seeded by |
| --- | --- | --- |
| `~/dotbrain/config.yaml` | Machine: shared infrastructure | `dotbrain bootstrap` |
| `~/dotbrain/skills/skills.yaml` | Machine: global skills | `dotbrain bootstrap` |
| `~/dotbrain/agents/agents.yaml` | Machine: global subagents | `dotbrain bootstrap` |
| `brainspaces/<name>/.brain/project.yaml` | One project | `dotbrain wire` |

After editing project declarations, run `dotbrain refresh` (or `dotbrain refresh --all`). Global
asset changes use `dotbrain skills link --scope global` or `dotbrain agents link --scope global`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOTBRAIN_HOME` | `~/dotbrain` (`%USERPROFILE%\dotbrain` on Windows) | Where Brainspaces and config live |

## `config.yaml`

Only needed for [server-mode](beads-backend.md#server-mode) Beads. The seeded file has the block
commented out.

```yaml
# ~/dotbrain/config.yaml
version: 3

beads:
  server:
    host: db.example.internal
    port: "3307"
    user: beads
    ssh_host: bastion.example.internal   # optional SSH hop, used by beads drop-db
```

::: warning
Never put credentials in `config.yaml`. Keep them in your secrets store.
:::

## `project.yaml`

Project identity and deviations from the global defaults. A project using server-mode Beads and one
extra skill looks like this:

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
execution-engine: beads

agents:            # which agent workspaces dotbrain wires
  - claude
  - codex

public-tracker: gh            # none | gh | linear
public-tracker-id: owner/repo

beads:                        # deviations from global defaults only
  mode: server                # embedded | server | none
  remote: https://doltremoteapi.dolthub.com/owner/repo
  database: project_beads

skills:                       # extra skills for this project's workspaces
  - some-collection/some-skill

# subagents:                  # project-only subagents; packaged subagents are always wired
#   - some-project-only-subagent
```

| Key | Default | Meaning |
| --- | --- | --- |
| `execution-engine` | `beads` | The private execution backend |
| `agents` | `[claude, codex]` | Agent workspaces to wire into the repo |
| `public-tracker` | `none` | Public issue intake: `none`, `gh`, or `linear` |
| `public-tracker-id` | — | The tracker's identifier, such as `owner/repo` for GitHub |
| `beads.mode` | `server` when a server host is configured; otherwise `embedded` | `embedded`, `server`, or `none` |
| `beads.remote` | — | Dolt remote for an embedded tracker |
| `beads.database` | project name | Server database name |
| `skills` | `[]` | Skills linked into this project's workspaces |
| `subagents` | `[]` | Project-only subagents in addition to the packaged subagents |

`public-tracker` sets up public issue intake and contributor collaboration. It never mirrors the
private work graph or turns private work into public issues; see the `triage-public` skill.

::: info
`dotbrain refresh` preserves project declarations byte-for-byte. Intentional Beads configuration
updates preserve unrelated keys, unknown nested values, and explicit empty selections; YAML
comments may be reformatted during those explicit updates.
:::

## `skills/skills.yaml`

Your global skills, linked into every agent session on this machine. List paths to skill folders
under `~/dotbrain/skills/`:

```yaml
# ~/dotbrain/skills/skills.yaml
version: 1
targets:
  claude-code: ~/.claude/skills
  codex: ~/.codex/skills
global_extra:
  - my-collection/my-skill
  - another-collection        # select every descendant skill
```

An entry containing `SKILL.md` selects that one skill. Otherwise its directory expands recursively
to descendants containing `SKILL.md`, excluding `node_modules`. Overlapping entries selecting the
same source are deduplicated. Distinct sources with the same destination name fail before any
linking or pruning; missing paths and empty bundles also fail. Adding or removing a skill in a
selected bundle takes effect on the next reconciliation without rewriting this declaration.

## `agents/agents.yaml`

Global subagents delivered into your personal agent homes. Removing an entry prunes its managed
resource on the next `dotbrain agents link --scope global`.

```yaml
# ~/dotbrain/agents/agents.yaml
# targets:
#   claude-code: ~/.claude/agents
#   codex: ~/.codex/agents
global:
  - some-shared-subagent
```

Skills and Claude agent definitions are symlinks. Codex agent definitions are disposable real
TOML copies with the ownership marker `# dotbrain-managed-agent: v1`; edit source definitions under
the private `agents/` root, not delivered copies. Dotbrain migrates owned Codex symlinks,
overwrites marked copies, and preserves unmarked files and foreign links. A conflicting user-owned
filename is reported instead of replaced.

Runtime flags use `--runtime claude|codex|all`. YAML target keys retain `claude-code` and `codex`.
Project linking defaults to the current wired checkout; `--scope global` is explicit and conflicts
with project selectors or `--all`.
