# Configuration

Most setups never edit configuration. When you do, there are two files, both in your private
dotbrain home: one for the machine and one per project.

```mermaid
treeView-beta
  accTitle: Where dotbrain's configuration files live
  ~/dotbrain/
    config.yaml ## machine: every global setting
    skills/ ## your skill sources
    subagents/ ## your custom subagent sources
    brainspaces/
      my-app/
        .brain/
          project.yaml ## one project
```

| File | Scope | Seeded by |
| --- | --- | --- |
| `~/dotbrain/config.yaml` | Machine: infrastructure, runtime profiles, global skills and subagents | `dotbrain bootstrap` |
| `brainspaces/<name>/.brain/project.yaml` | One project | `dotbrain wire` |

After editing project declarations, run `dotbrain refresh` (or `dotbrain refresh --all`). Global
asset changes use `dotbrain skills link --scope global` or `dotbrain subagents link --scope global`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOTBRAIN_HOME` | `~/dotbrain` (`%USERPROFILE%\dotbrain` on Windows) | Where Brainspaces and config live |
| `HERMES_HOME` | `~/.hermes` | Hermes's own home; dotbrain puts its Hermes plugin copy and global Hermes skills there |
| `XDG_CONFIG_HOME` | `~/.config` | Parent of OpenCode's config directory; dotbrain puts its OpenCode plugin file, packaged skills, and global OpenCode skills under `$XDG_CONFIG_HOME/opencode` |
| `PI_CODING_AGENT_DIR` | `~/.pi/agent` | Pi's agent directory; dotbrain puts its Pi extension copy and global Pi skills there |

## `config.yaml`

Every global setting lives here: [server-mode](beads-backend.md#server-mode) Beads,
[home sync](#sync), extra runtime homes, and the skills and subagents delivered to your personal
agent homes. The seeded file has every block commented out.

```yaml
# ~/dotbrain/config.yaml
version: 4

beads:
  server:
    host: db.example.internal
    port: "3307"
    user: beads
    ssh_host: bastion.example.internal   # optional SSH hop, used by beads drop-db

profiles:                     # extra Claude Code and Codex homes
  claude-code: [~/.claude-work]
  codex: [~/.codex-work]

skills:                       # global skills, under ~/dotbrain/skills/
  - my-collection/my-skill
  - another-collection        # select every descendant skill

subagents:                    # custom subagents, under ~/dotbrain/subagents/
  - some-shared-subagent
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
# Omit agents to follow this machine; an explicit list is exact.
agents:            # claude, codex, hermes, opencode, pi, cursor
  - claude
  - codex

beads:                        # deviations from global defaults only
  mode: server                # embedded | server | none
  remote: https://doltremoteapi.dolthub.com/owner/repo
  database: project_beads

skills:                       # extra skills for this project's workspaces
  - some-collection/some-skill

subagents:                    # project-only custom subagents
  - some-project-only-subagent

pstack:
  enabled: false              # explicit opt-in; source required when true
```

| Key | Default | Meaning |
| --- | --- | --- |
| `agents` | Runtimes set up on this machine | Claude and Codex when their CLI is on PATH; [`hermes`](getting-started.md#hermes), [`opencode`](getting-started.md#opencode), [`pi`](getting-started.md#pi), and [`cursor`](getting-started.md#cursor) when their dotbrain-owned delivery exists. An explicit list is exact; `[]` disables all. New projects leave this key commented out; existing lists are preserved. |
| `beads.mode` | `server` when a server host is configured; otherwise `embedded` | `embedded`, `server`, or `none` |
| `beads.remote` | — | Dolt remote for an embedded tracker |
| `beads.database` | project name | Server database name |
| `skills` | `[]` | Skills linked into this project's workspaces |
| `subagents` | `[]` | Project-only custom subagents |

Refresh warns about existing workspaces outside the resolved `agents` set and leaves everything in them untouched.

Codex project skills use `<checkout>/.agents/skills/`, independently of its `.codex/`
configuration and subagents. Global skills and profiles retain their existing homes.
See [skill reconciliation](skills.md#select-and-reconcile-skills) for legacy-link migration and collisions.

### Optional pstack {#pstack}

The core works without pstack. The project-only `pstack` mapping accepts:

| Key | Default | Meaning |
| --- | --- | --- |
| `pstack.enabled` | `false` | YAML boolean selecting the optional project engineering mode. Requires an initialized, reachable Beads backend. |
| `pstack.source` | — | Explicit external source checkout, absolute or starting with `~/`; required when enabled. |

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
pstack:
  enabled: true
  source: ~/pstack
```

Unknown pstack keys, non-boolean `enabled`, and relative or missing enabled source
paths fail with actionable errors. Source validation requires the clean complete
pstack checkout pinned in [workflow setup](workflow.md#dependency). `wire`,
`refresh`, and project `skills link` reconcile the selected mode; `doctor` checks
its dependency, backend and delivery. No command installs or updates pstack.

Delivery is limited to configured Claude Code and Codex project workspaces. The
ignored `.dotbrain-pstack.json` and separate owned integration cache are generated
resources, not configuration to edit. Disabling the mode and refreshing removes
intact owned delivery; modified and foreign resources are preserved and reported.
Restart sessions after changes. See [qualification scope](workflow.md#qualification)
for the boundary between structural checks and native behavior evidence.

`packaged-subagents`, `retro`, `execution-engine`, `public-tracker`, and
`public-tracker-id` are obsolete and ignored. Refresh reports them without
rewriting user declarations. Remove them explicitly after reviewing
[upgrade guidance](upgrading.md), preserving unrelated settings.

::: info
`dotbrain refresh` preserves project declarations byte-for-byte. Intentional Beads configuration
updates preserve unrelated keys, unknown nested values, and explicit empty selections; YAML
comments may be reformatted during those explicit updates.
:::

## Global skills and profiles {#global-skills}

`skills:` lists your global skills, linked into every agent session on this machine. Each entry is
a path to a skill folder under `~/dotbrain/skills/`.

Claude Code and Codex receive skills in `<home>/skills` for their default homes (`~/.claude`
and `~/.codex`) and each extra home listed in `profiles`. Missing profile homes are silently
skipped, so the file can be shared across machines. Other runtimes keep their own relocation
variables and plugin installation, and do not accept profiles.

Homes inside a wired checkout or worktree are rejected before their links are changed; symlinked
home directories are supported. Doctor also checks the dotbrain plugin in each Claude Code home.

An entry containing `SKILL.md` selects that one skill. Otherwise its directory expands recursively
to descendants containing `SKILL.md`, excluding `node_modules`. Overlapping entries selecting the
same source are deduplicated. Distinct sources with the same destination name fail before any
linking or pruning; missing paths and empty bundles also fail. Adding or removing a skill in a
selected bundle takes effect on the next reconciliation without rewriting this declaration.

## Global subagents {#global-subagents}

`subagents:` lists custom subagents delivered into your personal agent homes. Each name is a
source under `~/dotbrain/subagents/claude/<name>.md` or `~/dotbrain/subagents/codex/<name>.toml`.
Removing an entry prunes its managed resource on the next `dotbrain subagents link --scope global`.

The core ships no workflow agents. Every selected name refers to your own source.
The `dotbrain-` prefix remains reserved for safe handling of old resources.

Claude Code and Codex receive agents in `<home>/agents`, using their default homes and the same
`profiles`. Missing profiles are skipped; destinations inside wired checkouts are reported and
skipped.

Skills and Claude agent definitions are symlinks. Codex agent definitions are disposable real
TOML copies with the ownership marker `# dotbrain-managed-agent: v1`; edit source definitions under
`~/dotbrain/subagents/`, not delivered copies. Dotbrain migrates owned Codex symlinks,
overwrites marked copies, and preserves unmarked files and foreign links. A conflicting user-owned
filename is reported instead of replaced.

Runtime flags use `--runtime claude|codex|hermes|opencode|pi|cursor|all`. Profile keys are
`claude-code` and `codex`. Hermes, OpenCode, Pi, and Cursor receive no subagents.
Project linking defaults to the current wired checkout; `--scope global` is explicit and conflicts
with project selectors or `--all`.

## Upgrading from earlier versions {#upgrading}

Read [the breaking upgrade guide](upgrading.md) before changing a live installation.
The current core has no legacy engineering workflow mode.

Older global settings may still need the existing bootstrap migration to
`config.yaml` version 4. It merges supported profiles, skills and custom subagent
selections, saves originals under `~/dotbrain/.cache/config-backups/`, and reports
retired entries. Runtime default targets are dropped; custom Claude Code/Codex
homes become profiles. Sources under old `agents/` move to `subagents/` only when
safe. Unknown or conflicting declarations and competing source folders stop
migration rather than guessing. Global delivery waits until cleanup completes.
Use the reported backups for manual recovery and inspect notices before retrying.
This migration neither selects pstack nor restores retired packaged roles.
