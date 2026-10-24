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
| `HERMES_HOME` | `~/.hermes` | Hermes's own home; dotbrain puts its Hermes plugin copy and global Hermes skills there |
| `XDG_CONFIG_HOME` | `~/.config` | Parent of OpenCode's config directory; dotbrain puts its OpenCode plugin file, packaged skills, and global OpenCode skills under `$XDG_CONFIG_HOME/opencode` |
| `PI_CODING_AGENT_DIR` | `~/.pi/agent` | Pi's agent directory; dotbrain puts its Pi extension copy and global Pi skills there |

## `config.yaml`

Only needed for [server-mode](beads-backend.md#server-mode) Beads or to change
[home sync](#sync). The seeded file has the Beads block commented out.

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

### `sync:` {#sync}

[Home sync](session-context.md#home-sync) records uncommitted changes in the dotbrain home as
commits and exchanges them with the home's remote. It is on when the section is absent. Add the
section only to turn sync off or to change the size limit:

```yaml
# ~/dotbrain/config.yaml
sync:
  enabled: false        # default true
  max-file-size: 5MB    # default 1MB
```

| Key | Default | Meaning |
| --- | --- | --- |
| `sync.enabled` | `true` | `false` turns off the hooks' sync and `dotbrain sync`; you commit and push the home yourself |
| `sync.max-file-size` | `1MB` | Files larger than this stay uncommitted and are reported. A byte count such as `1048576`, or a size such as `500KB`, `1MB`, or `2GB` (1 KB = 1024 bytes) |

The remote is the upstream of the home's current branch; there is no remote setting.
`config.yaml` is shared by every machine through that remote, so the setting applies on all of
them. Sync names each machine in its commit messages by hostname.

## `project.yaml`

Project identity and deviations from the global defaults. A project using server-mode Beads and one
extra skill looks like this:

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
execution-engine: beads

# Omit agents to follow this machine; an explicit list is exact.
agents:            # claude, codex, hermes, opencode, pi, cursor
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
| `agents` | Runtimes set up on this machine | Claude and Codex when their CLI is on PATH; [`hermes`](getting-started.md#hermes), [`opencode`](getting-started.md#opencode), [`pi`](getting-started.md#pi), and [`cursor`](getting-started.md#cursor) when their dotbrain-owned delivery exists. An explicit list is exact; `[]` disables all. New projects leave this key commented out; existing lists are preserved. |
| `public-tracker` | `none` | Public issue intake: `none`, `gh`, or `linear` |
| `public-tracker-id` | — | The tracker's identifier, such as `owner/repo` for GitHub |
| `beads.mode` | `server` when a server host is configured; otherwise `embedded` | `embedded`, `server`, or `none` |
| `beads.remote` | — | Dolt remote for an embedded tracker |
| `beads.database` | project name | Server database name |
| `skills` | `[]` | Skills linked into this project's workspaces |
| `subagents` | `[]` | Project-only subagents in addition to the packaged subagents |
| `retro.promotion.auto-deliver` | `false` | Skill-read setting: allow unattended commit/push/PR delivery of rule proposals |
| `retro.promotion.destinations` | `[]` | Allowed existing public guides as repo-relative paths; a nonempty array is required for auto-delivery |

Refresh warns about existing workspaces outside the resolved `agents` set and leaves everything in them untouched.

Codex project skills use `<checkout>/.agents/skills/`, independently of its `.codex/`
configuration and subagents. Global skills and profiles retain their existing homes.
See [skill reconciliation](skills.md#select-and-reconcile-skills) for legacy-link migration and collisions.

`public-tracker` sets up public issue intake and contributor collaboration. It never mirrors the
private work graph or turns private work into public issues; see the `triage-public` skill.

`run-retro` reads its settings directly; they add no CLI delivery command. With auto-delivery
disabled or unset, it updates private findings, discovers the repository's guidance conventions,
and suggests a destination and rule for your decision. You can authorize an individual PR or
enable standing delivery to an agreed destination, for example:

```yaml
# project.yaml — opt in only after agreeing on this repository's destination
retro:
  promotion:
    auto-deliver: true
    destinations:
      - CONTRIBUTING.md
      - docs/code-standards.md
```

Each destination must exist inside the repository. The skill selects the best fit per finding,
amending existing guidance without copying a rule into every file. If scope is ambiguous or no
allowed file fits, it suggests the choice to you. A new rules file needs explicit agreement;
the skill never assumes a repository should adopt `RULES.md`. Approval and merge remain human-owned.
Disabling auto-delivery leaves private capture and read-only reconciliation available.

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
profiles:
  claude-code: [~/.claude-work]
  codex: [~/.codex-work]
global_extra:
  - my-collection/my-skill
  - another-collection        # select every descendant skill
```

Claude Code and Codex receive skills in `<home>/skills` for their default homes (`~/.claude`
and `~/.codex`) and each extra home listed in `profiles`. Missing profile homes are silently
skipped, so the file can be shared across machines. Other runtimes retain their existing
relocation and plugin installation requirements and do not accept profiles.

Homes inside a wired checkout or worktree are rejected before their links are changed; symlinked
home directories are supported. Doctor also checks the dotbrain plugin in each Claude Code home.
Legacy `targets` entries matching the default skills folder are ignored. A custom skills target
uses its parent as an extra home and prints a notice to move that home to `profiles`.

An entry containing `SKILL.md` selects that one skill. Otherwise its directory expands recursively
to descendants containing `SKILL.md`, excluding `node_modules`. Overlapping entries selecting the
same source are deduplicated. Distinct sources with the same destination name fail before any
linking or pruning; missing paths and empty bundles also fail. Adding or removing a skill in a
selected bundle takes effect on the next reconciliation without rewriting this declaration.

## `agents/agents.yaml`

Global subagents delivered into your personal agent homes. Removing an entry prunes its managed
resource on the next `dotbrain agents link --scope global`.

Claude Code and Codex receive agents in `<home>/agents`, using their default homes and the
`profiles:` in `skills/skills.yaml`. Missing profiles are skipped; destinations inside wired
checkouts are reported and skipped. Legacy `targets:` matching the default are silently ignored;
custom targets use their parent as an extra home, with a notice to move it to `skills.yaml` `profiles:`.

```yaml
# ~/dotbrain/agents/agents.yaml
# Extra runtime homes are configured in skills/skills.yaml under profiles.
global:
  - some-shared-subagent
```

Skills and Claude agent definitions are symlinks. Codex agent definitions are disposable real
TOML copies with the ownership marker `# dotbrain-managed-agent: v1`; edit source definitions under
the private `agents/` root, not delivered copies. Dotbrain migrates owned Codex symlinks,
overwrites marked copies, and preserves unmarked files and foreign links. A conflicting user-owned
filename is reported instead of replaced.

Runtime flags use `--runtime claude|codex|hermes|opencode|pi|cursor|all`. YAML target keys are
`claude-code`, `codex`, `hermes`, `opencode`, `pi`, and `cursor`. Hermes, OpenCode, Pi, and Cursor have no
subagent target.
Project linking defaults to the current wired checkout; `--scope global` is explicit and conflicts
with project selectors or `--all`.
