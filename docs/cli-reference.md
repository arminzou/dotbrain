# CLI Reference

Every public `dotbrain` command, grouped by task. Run any command with `--help` for the same
information in the terminal.

Human reports group changes and problems by target, shorten home paths to `~`, and use tables
for catalogs and project inspection. Empty lists, previews, and skipped work are explicit.
Doctor shows problems and warnings first; use `doctor -v` to include every healthy check.
Colors follow terminal capabilities; redirected output stays plain.

Finite reports support `--json`: stdout contains one result with command, overall status,
per-target results, and errors. Finding severities are `info`, `warning`, and `error`; warnings
alone do not cause failure. Exit codes are `0` for success, `1` for operational failure or a
partially failed batch, and `2` for invalid invocation or selection.

JSON consumers must replace checks for `severity: advisory` with `severity: warning`.
The old severity is no longer emitted; other result fields and exit codes are unchanged.

## Commands at a Glance

| Command | Does |
| --- | --- |
| [`bootstrap`](#dotbrain-bootstrap) | Prepare this machine for dotbrain: global skill and subagent links. |
| [`doctor`](#dotbrain-doctor) | Read-only health check of machine readiness and selected project setup. |
| [`wire`](#dotbrain-wire) | Create a Brainspace or attach a checkout, including a linked worktree. |
| [`refresh`](#dotbrain-refresh) | Repair setup while preserving project declarations and content. |
| [`unwire`](#dotbrain-unwire) | Detach a checkout while retaining its Brainspace and tracker databases. |
| [`projects list`](#dotbrain-projects-list) | List every registered project using local declarations and wiring. |
| [`projects show`](#dotbrain-projects-show) | Inspect the current wired project or a named project's registered checkout. |
| [`skills list`](#dotbrain-skills-list) | Discover locally available skills. |
| [`skills link`](#dotbrain-skills-link) | Reconcile selected skills in project or explicit global scope. |
| [`agents list`](#dotbrain-agents-list) | Discover locally available agents. |
| [`agents link`](#dotbrain-agents-link) | Reconcile selected agents in project or explicit global scope. |
| [`beads sync`](#dotbrain-beads-sync) | Hydrate declared local tracker bindings and pull configured remotes; never push. |
| [`beads migrate`](#dotbrain-beads-migrate) | Migrate embedded trackers to a server, keeping history and rollback backups. |
| [`beads list-db`](#dotbrain-beads-list-db) | List remote database identifiers, including databases without a Brainspace. |
| [`beads drop-db`](#dotbrain-beads-drop-db) | Explicitly delete a remote database; never infer it from the current project. |
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
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--json` | — | Emit one structured result. |

### `dotbrain doctor` {#dotbrain-doctor}

Read-only health check of machine readiness and selected project setup.

```text
dotbrain doctor [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--project` *text* | — | Select a named Brainspace. |
| `--all` | — | Inspect every registered project. |
| `--verbose`, `-v` | — | Show every healthy check as well as problems and warnings. |
| `--json` | — | Emit one structured result. |

## Projects

Connect code repos to Brainspaces and keep them in sync. See [Wiring](wiring.md).

### `dotbrain wire` {#dotbrain-wire}

Create a Brainspace or attach a checkout, including a linked worktree.

```text
dotbrain wire [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--repo` *path* | — | Checkout to attach; defaults to the current Git checkout. |
| `--project` *text* | — | Select a named Brainspace. |
| `--no-repo` | — | Create a Brain-only project; requires `--project`. |
| `--skip-beads` | — | Create without a tracker. |
| `--remote` *text* | — | Dolt remote for initial tracker creation. |
| `--server-host` *text* | — | Dolt server host; defaults to config. |
| `--server-port` *text* | — | Dolt server port; defaults to config. |
| `--server-user` *text* | — | Dolt server user; defaults to config. |
| `--database` *text* | — | Tracker database; defaults to project name. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain refresh` {#dotbrain-refresh}

Repair setup while preserving project declarations and content.

```text
dotbrain refresh [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--all` | — | Refresh all registered projects. |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--json` | — | Emit one structured result. |

### `dotbrain unwire` {#dotbrain-unwire}

Detach a checkout while retaining its Brainspace and tracker databases.

```text
dotbrain unwire [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--repo` *path* | — | Checkout to detach. |
| `--project` *text* | — | Select a named Brainspace. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain projects list` {#dotbrain-projects-list}

List every registered project using local declarations and wiring.

```text
dotbrain projects list [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain projects show` {#dotbrain-projects-show}

Inspect the current wired project or a named project's registered checkout.

```text
dotbrain projects show [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

## Skills and agents

Link skills and vendor-native subagents into agent runtimes. See [Skills](skills.md).

### `dotbrain skills list` {#dotbrain-skills-list}

Discover locally available skills.

```text
dotbrain skills list [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--project` *text* | — | — |
| `--json` | — | Emit one structured result. |

### `dotbrain skills link` {#dotbrain-skills-link}

Reconcile selected skills in project or explicit global scope.

```text
dotbrain skills link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--scope` *text* | `project` | — |
| `--project` *text* | — | — |
| `--repo` *path* | — | — |
| `--all` | — | — |
| `--json` | — | Emit one structured result. |

### `dotbrain agents list` {#dotbrain-agents-list}

Discover locally available agents.

```text
dotbrain agents list [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--project` *text* | — | — |
| `--json` | — | Emit one structured result. |

### `dotbrain agents link` {#dotbrain-agents-link}

Reconcile selected agents in project or explicit global scope.

```text
dotbrain agents link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, or all. |
| `--scope` *text* | `project` | — |
| `--project` *text* | — | — |
| `--repo` *path* | — | — |
| `--all` | — | — |
| `--json` | — | Emit one structured result. |

## Beads

Manage the Beads tracker's state and backend. See [Beads backend](beads-backend.md).

### `dotbrain beads sync` {#dotbrain-beads-sync}

Hydrate declared local tracker bindings and pull configured remotes; never push.

```text
dotbrain beads sync [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--all` | — | Sync every registered project. |
| `--dry-run` | — | Preview tracker hydration and configured pulls. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain beads migrate` {#dotbrain-beads-migrate}

Migrate embedded trackers to a server, keeping history and rollback backups.

```text
dotbrain beads migrate [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--all` | — | Migrate every registered project. |
| `--server-host` *text* | — | Target Dolt server host; defaults to config. |
| `--server-port` *text* | — | Target Dolt server port; defaults to config. |
| `--server-user` *text* | — | Target Dolt server user; defaults to config. |
| `--database` *text* | — | Database override for a single project. |
| `--dry-run` | — | Preview the history-preserving migration. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain beads list-db` {#dotbrain-beads-list-db}

List remote database identifiers, including databases without a Brainspace.

```text
dotbrain beads list-db [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--server-host` *text* | — | Dolt server host; defaults to config. |
| `--server-port` *text* | — | Dolt server port; defaults to config. |
| `--server-user` *text* | — | Dolt server user; defaults to config. |
| `--ssh-host` *text* | — | Optional SSH hop; defaults to config. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain beads drop-db` {#dotbrain-beads-drop-db}

Explicitly delete a remote database; never infer it from the current project.

```text
dotbrain beads drop-db [OPTIONS] NAME
```

| Argument | Description |
| --- | --- |
| `NAME` | Database identifier, including an orphaned database. |

| Option | Default | Description |
| --- | --- | --- |
| `--yes` | — | Confirm the destructive drop. |
| `--dry-run` | — | Preview without deleting. |
| `--server-host` *text* | — | Dolt server host; defaults to config. |
| `--server-port` *text* | — | Dolt server port; defaults to config. |
| `--server-user` *text* | — | Dolt server user; defaults to config. |
| `--ssh-host` *text* | — | Optional SSH hop; defaults to config. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

## Brain site

Set up and run a Brain's private site. See [Brain site](brain-site.md).

### `dotbrain site init` {#dotbrain-site-init}

Give a Brain a site: create .brain/site/ with site.yaml, the home page, and the manual.

```text
dotbrain site init [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--title` *text* | — | Site title. Defaults to '&lt;name&gt; Brain'. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain site dev` {#dotbrain-site-dev}

Serve the Brain site locally with live reload (127.0.0.1).

```text
dotbrain site dev [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--home` *path* | — | Override the private data root. |

### `dotbrain site build` {#dotbrain-site-build}

Build the Brain site; fails on a nav link to a missing page.

```text
dotbrain site build [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--home` *path* | — | Override the private data root. |
| `--json` | — | Emit one structured result. |

### `dotbrain site preview` {#dotbrain-site-preview}

Serve the last build locally (127.0.0.1).

```text
dotbrain site preview [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--home` *path* | — | Override the private data root. |

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
