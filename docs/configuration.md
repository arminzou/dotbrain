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

After editing a file, run `dotbrain refresh` (or `dotbrain refresh --all`) to apply it.

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

# subagents:                  # project-only subagents; the packaged four are always wired
#   - some-project-only-subagent
```

| Key | Default | Meaning |
| --- | --- | --- |
| `execution-engine` | `beads` | The private execution backend |
| `agents` | `[claude, codex]` | Agent workspaces to wire into the repo |
| `public-tracker` | `none` | Public issue intake: `none`, `gh`, or `linear` |
| `public-tracker-id` | — | The tracker's identifier, such as `owner/repo` for GitHub |
| `beads.mode` | `embedded` | `embedded`, `server`, or `none` |
| `beads.remote` | — | Dolt remote for an embedded tracker |
| `beads.database` | project name | Server database name |
| `skills` | `[]` | Skills linked into this project's workspaces |
| `subagents` | `[]` | Project-only subagents in addition to the packaged four |

`public-tracker` sets up public issue intake and contributor collaboration. It never mirrors the
private execution graph or turns private work into public issues; see the `triage-public` skill.

::: info
`dotbrain refresh` may rewrite the shared sections of `project.yaml`.
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
```

## `agents/agents.yaml`

Global subagents linked into your personal agent homes. Removing an entry prunes its link on the
next relink.

```yaml
# ~/dotbrain/agents/agents.yaml
# targets:
#   claude-code: ~/.claude/agents
#   codex: ~/.codex/agents
global:
  - some-shared-subagent
```
