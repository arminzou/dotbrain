# CLI Reference

Every public `dotbrain` command, grouped by task. Run any command with `--help` for the same
information in the terminal.

## Commands at a Glance

| Command | Does |
| --- | --- |
| [`bootstrap`](#dotbrain-bootstrap) | Prepare this machine for dotbrain: global skill and subagent links. |
| [`doctor`](#dotbrain-doctor) | Read-only health check: machine readiness, project wiring, beads state drift. |
| [`update`](#dotbrain-update) | Print the command that upgrades this CLI with the tool that installed it. |
| [`wire`](#dotbrain-wire) | Create or repair a project Brainspace and wire an adopter repo. |
| [`refresh`](#dotbrain-refresh) | Refresh Brain/workspace files, repo links, beads state, and project skills. |
| [`unwire`](#dotbrain-unwire) | Disconnect an adopter repo from its Brainspace. |
| [`skills link`](#dotbrain-skills-link) | Link skills into agent runtimes. |
| [`agents link`](#dotbrain-agents-link) | Link vendor-native subagents into agent runtimes. |
| [`beads load`](#dotbrain-beads-load) | Hydrate local beads state from tracked declarations: attach server trackers, init embedded ones, then pull. |
| [`beads migrate`](#dotbrain-beads-migrate) | Migrate a local-only (embedded Dolt) beads tracker onto the remote sql-server, history intact. |
| [`beads list-db`](#dotbrain-beads-list-db) | List the databases on the shared Dolt sql-server. |
| [`beads drop-db`](#dotbrain-beads-drop-db) | Drop a project's remote beads database on the shared Dolt sql-server. |
| [`site init`](#dotbrain-site-init) | Give a Brain a site: create .brain/site/ with site.yaml, the home page, and the manual. |
| [`site dev`](#dotbrain-site-dev) | Serve the Brain site locally with live reload (127.0.0.1). |
| [`site build`](#dotbrain-site-build) | Build the Brain site; fails on a nav link to a missing page. |
| [`site preview`](#dotbrain-site-preview) | Serve the last build locally (127.0.0.1). |
| [`hook session-start`](#dotbrain-hook-session-start) | Emit a wired repo's Brain context. |

## Setup

Prepare a machine and check its health. See [Getting started](getting-started.md).

### `dotbrain bootstrap` {#dotbrain-bootstrap}

Prepare this machine for dotbrain: global skill and subagent links.

```text
dotbrain bootstrap [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--only` *text* | — | Limit linking to one step. The only step is skills: global skill and subagent links. |
| `--skip-skills` | — | Seed the data root but skip global skill and subagent links. |

### `dotbrain doctor` {#dotbrain-doctor}

Read-only health check: machine readiness, project wiring, beads state drift.

```text
dotbrain doctor
```

### `dotbrain update` {#dotbrain-update}

Print the command that upgrades this CLI with the tool that installed it.

```text
dotbrain update
```

## Projects

Connect code repos to Brainspaces and keep them in sync. See [Wiring](wiring.md).

### `dotbrain wire` {#dotbrain-wire}

Create or repair a project Brainspace and wire an adopter repo.

Without `--all`: wire one project. With `--all`: reconcile every Brainspace.

```text
dotbrain wire [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--all` | — | Wire every adopter repo to its Brainspace (brain seeding and symlinks). |
| `--repo` *text* | — | Repo to wire. Defaults to the current git repo. |
| `--name` *text* | — | Project/Brainspace name. Defaults to repo dir name. |
| `--dotbrain` *text* | — | dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred. |
| `--skip-beads` | — | Do not initialize .beads when missing. |
| `--beads-remote` *text* | — | Initialize beads from this Dolt remote. |
| `--beads-server-host` *text* | — | Init beads against an external Dolt sql-server. Defaults to beads.server.host in config.yaml. |
| `--beads-server-port` *text* | — | Dolt sql-server port. Defaults to beads.server.port in config.yaml. |
| `--beads-server-user` *text* | — | Dolt sql-server user. Defaults to beads.server.user in config.yaml. |
| `--beads-database` *text* | — | Dolt database name. Defaults to project name. |
| `--no-repo` | — | Create a brain-only Brainspace (no code repo). Requires `--name`. |
| `--repo-base` *path* | — | Base directory for adopter repos (default: ~/repos/projects). |

### `dotbrain refresh` {#dotbrain-refresh}

Refresh Brain/workspace files, repo links, beads state, and project skills.

```text
dotbrain refresh [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--all` | — | Refresh every project workspace. |
| `--name` *text* | — | Refresh one project by Brainspace name. |
| `--repo-base` *path* | — | Base directory for repo discovery. |

### `dotbrain unwire` {#dotbrain-unwire}

Disconnect an adopter repo from its Brainspace.

Offboards the Brainspace only (keep/archive/delete). To drop a server-backend project's remote beads database, use `dotbrain beads drop-db` separately.

```text
dotbrain unwire [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--all` | — | Unwire every project Brainspace (keep only; see per-project `--archive`/`--delete` for destructive offboard). |
| `--repo` *path* | — | Adopter repo path; defaults to cwd |
| `--name` *text* | — | Project/Brainspace name |
| `--no-repo` | — | Only offboard the named Brainspace; do not edit an adopter repo. |
| `--archive` | — | Move Brainspace to &lt;data-dir&gt;/.archive/ |
| `--delete` | — | Remove the Brainspace (destructive) |
| `--dry-run` | — | Preview the offboard without performing it. |

## Skills and agents

Link skills and vendor-native subagents into agent runtimes. See [Skills](skills.md).

### `dotbrain skills link` {#dotbrain-skills-link}

Link skills into agent runtimes.

Both scopes are curated include-lists. Project links each project's `project.yaml` `skills:` selection into its agent workspaces. Global links the operator's optional global selection into each runtime's skills directory.

```text
dotbrain skills link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--target` *text* | `all` | claude-code \| codex \| all |
| `--scope` *text* | `all` | global \| project \| all |
| `--project` *text* | — | limit project scope to one Brainspace by name |
| `--repo` *text* | — | Checkout to link into (e.g. a linked worktree). Requires `--project` and project scope. |

### `dotbrain agents link` {#dotbrain-agents-link}

Link vendor-native subagents into agent runtimes.

```text
dotbrain agents link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--target` *text* | `all` | claude-code \| codex \| all |
| `--scope` *text* | `all` | global \| project \| all |
| `--project` *text* | — | Limit project linking to a single Brainspace by name. |
| `--repo` *text* | — | Checkout to link into (e.g. a linked worktree). Requires `--project` and project scope. |

## Beads

Manage the Beads tracker's state and backend. See [Beads backend](beads-backend.md).

### `dotbrain beads load` {#dotbrain-beads-load}

Hydrate local beads state from tracked declarations: attach server trackers, init embedded ones, then pull. Pull-only reconcile: never pushes, never touches symlinks or hooks.

Without `--all`: load one project (by `--name`, or the `--repo`/cwd repo). With `--all`: every brainspace root declared to use beads.

```text
dotbrain beads load [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--all` | — | Load tracker state for every Brainspace. |
| `--repo` *text* | — | Repo whose Brainspace to load. Defaults to the current git repo. |
| `--name` *text* | — | Project/Brainspace name to load. |
| `--dotbrain` *text* | — | dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred. |
| `--dry-run` | — | Preview what would be hydrated/pulled without mutating anything. |

### `dotbrain beads migrate` {#dotbrain-beads-migrate}

Migrate a local-only (embedded Dolt) beads tracker onto the remote sql-server, history intact.

```text
dotbrain beads migrate [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--repo` *text* | — | Wired repo path; project name is its dir name. |
| `--name` *text* | — | Project/Brainspace name to migrate. |
| `--all` | — | Migrate every embedded Brainspace. |
| `--dotbrain` *text* | — | dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred. |
| `--beads-server-host` *text* | — | Target Dolt sql-server host. Defaults to beads.server.host in config.yaml. |
| `--beads-server-port` *text* | — | Dolt sql-server port. Defaults to beads.server.port in config.yaml. |
| `--beads-server-user` *text* | — | Dolt sql-server user. Defaults to beads.server.user in config.yaml. |
| `--beads-database` *text* | — | Dolt database name (single-project only). Defaults to project name. |
| `--dry-run` | — | Print the planned bd sequence without running it. |

### `dotbrain beads list-db` {#dotbrain-beads-list-db}

List the databases on the shared Dolt sql-server.

```text
dotbrain beads list-db [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--beads-ssh-host` *text* | — | SSH hop that can reach the sql-server; empty connects directly. Defaults to beads.server.ssh_host. |
| `--beads-server-host` *text* | — | Dolt sql-server host. Defaults to beads.server.host. |
| `--beads-server-port` *text* | — | Dolt sql-server port. Defaults to beads.server.port. |
| `--beads-server-user` *text* | — | Dolt sql-server user. Defaults to beads.server.user. |

### `dotbrain beads drop-db` {#dotbrain-beads-drop-db}

Drop a project's remote beads database on the shared Dolt sql-server.

```text
dotbrain beads drop-db [OPTIONS] NAME
```

| Argument | Description |
| --- | --- |
| `NAME` | Beads database name to drop (usually the project name). |

| Option | Default | Description |
| --- | --- | --- |
| `--yes` | — | Confirm the destructive drop. |
| `--dry-run` | — | Preview the drop without running it. |
| `--beads-ssh-host` *text* | — | SSH hop that can reach the sql-server; empty connects directly. Defaults to beads.server.ssh_host. |
| `--beads-server-host` *text* | — | Dolt sql-server host. Defaults to beads.server.host. |
| `--beads-server-port` *text* | — | Dolt sql-server port. Defaults to beads.server.port. |
| `--beads-server-user` *text* | — | Dolt sql-server user. Defaults to beads.server.user. |

## Brain site

Set up and run a Brain's private site. See [Brain site](brain-site.md).

### `dotbrain site init` {#dotbrain-site-init}

Give a Brain a site: create .brain/site/ with site.yaml, the home page, and the manual.

```text
dotbrain site init [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--name` *text* | — | Brainspace name. Defaults to the current repo's .brain. |
| `--title` *text* | — | Site title. Defaults to '&lt;name&gt; Brain'. |

### `dotbrain site dev` {#dotbrain-site-dev}

Serve the Brain site locally with live reload (127.0.0.1).

```text
dotbrain site dev [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--name` *text* | — | Brainspace name. Defaults to the current repo's .brain. |

### `dotbrain site build` {#dotbrain-site-build}

Build the Brain site; fails on a nav link to a missing page.

```text
dotbrain site build [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--name` *text* | — | Brainspace name. Defaults to the current repo's .brain. |

### `dotbrain site preview` {#dotbrain-site-preview}

Serve the last build locally (127.0.0.1).

```text
dotbrain site preview [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--name` *text* | — | Brainspace name. Defaults to the current repo's .brain. |

## Internal

Run by the plugin's hooks, not by hand. See [Session context](session-context.md).

### `dotbrain hook session-start` {#dotbrain-hook-session-start}

Emit a wired repo's Brain context. Fail-open: silent and exit 0 when there is none.

```text
dotbrain hook session-start [ARGS]
```

| Argument | Description |
| --- | --- |
| `ARGS` | — |
