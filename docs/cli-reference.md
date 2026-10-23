# CLI Reference

Every public `dotbrain` command, grouped by task. Run any command with `--help` for the same
information in the terminal.

Human reports group changes and problems by target, shorten home paths to `~`, and use tables
for catalogs and project inspection. Empty lists, previews, and skipped work are explicit.
Doctor shows problems and warnings first; use `doctor -v` to include every healthy check.
Doctor warns when CLI and registered Claude Code plugin versions differ (upgrade both), when
the Brain's `DOTBRAIN.md` differs from the packaged convention (run `dotbrain refresh`), and
when every spec-linked epic of an active design is closed (run `close-design` or correct the lifecycle).
Unavailable drift inputs are skipped with an explanation in verbose and JSON output.
Runtime activation and session uncertainty are informational, shown with `doctor -v` and in
JSON; they do not count as passed checks. Missing registered hook files and failed plugin
checks remain warnings. With `--all`, a project whose shared `.repo` checkout is absent on this
machine is reported as skipped, not failed; a missing `.repo.local` checkout or an explicit
`--project` still fails.
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
| [`detach`](#dotbrain-detach) | Remove dotbrain's machine-wide delivery from a runtime. |
| [`doctor`](#dotbrain-doctor) | Read-only health check of machine readiness and selected project setup. |
| [`wire`](#dotbrain-wire) | Create a Brainspace or attach a checkout, including a linked worktree. |
| [`refresh`](#dotbrain-refresh) | Repair setup while preserving project declarations and content. |
| [`unwire`](#dotbrain-unwire) | Remove a checkout's wiring while retaining its Brainspace and tracker databases. |
| [`projects list`](#dotbrain-projects-list) | List every registered project using local declarations and wiring. |
| [`projects show`](#dotbrain-projects-show) | Inspect the current wired project or a named project's registered checkout. |
| [`check-head`](#dotbrain-check-head) | Check that a branch matches its accepted head without writing Git or tracker state. |
| [`skills list`](#dotbrain-skills-list) | Discover locally available skills. |
| [`skills link`](#dotbrain-skills-link) | Reconcile selected skills in project or explicit global scope. |
| [`agents list`](#dotbrain-agents-list) | Discover locally available agents. |
| [`agents link`](#dotbrain-agents-link) | Reconcile selected agents in project or explicit global scope. |
| [`beads sync`](#dotbrain-beads-sync) | Sync declared local tracker bindings and pull configured remotes; never push. |
| [`beads migrate`](#dotbrain-beads-migrate) | Migrate embedded trackers to a server, keeping history and rollback backups. |
| [`beads list-db`](#dotbrain-beads-list-db) | List remote database identifiers, including databases without a Brainspace. |
| [`beads drop-db`](#dotbrain-beads-drop-db) | Explicitly delete a remote database; never infer it from the current project. |
| [`sync`](#dotbrain-sync) | Record uncommitted home changes as sync commits, integrate the upstream, and push. |
| [`site init`](#dotbrain-site-init) | Give a Brain a site: create .brain/site/ with site.yaml, the home page, and the manual. |
| [`site dev`](#dotbrain-site-dev) | Serve the Brain site locally with live reload (127.0.0.1). |
| [`site build`](#dotbrain-site-build) | Build the Brain site; fails on a nav link to a missing page. |
| [`site preview`](#dotbrain-site-preview) | Serve the last build locally (127.0.0.1). |
| [`hook session-start`](#dotbrain-hook-session-start) | Sync the home (waiting at most 10 s), then emit a wired repo's Brain context. |
| [`hook stop`](#dotbrain-hook-stop) | Start a detached push-only home sync and return at once. |
| [`hook session-end`](#dotbrain-hook-session-end) | Start a detached full home sync and return at once. |
| [`hook run`](#dotbrain-hook-run) | Handle a session event for any runtime adapter, without reading a hook payload. |

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
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--json` | — | Emit one structured result. |

### `dotbrain detach` {#dotbrain-detach}

Remove dotbrain's machine-wide delivery from a runtime.

```text
dotbrain detach [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--runtime` *text* | — | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--home` *path* | — | Override the private data root. |
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
| `--verbose`, `-v` | — | Include healthy checks and informational context. |
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
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--json` | — | Emit one structured result. |

### `dotbrain unwire` {#dotbrain-unwire}

Remove a checkout's wiring while retaining its Brainspace and tracker databases.

```text
dotbrain unwire [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--repo` *path* | — | Checkout whose wiring to remove. |
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

### `dotbrain check-head` {#dotbrain-check-head}

Check that a branch matches its accepted head without writing Git or tracker state.

```text
dotbrain check-head [OPTIONS] ITEM
```

| Argument | Description |
| --- | --- |
| `ITEM` | Review bead or verified single work item. |

| Option | Default | Description |
| --- | --- | --- |
| `--branch` *text* | — | Local branch to check. Default: current branch. |
| `--repo` *path* | — | Checkout to inspect. Default: working directory. |
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
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--project` *text* | — | Show selections for a named Brainspace. |
| `--json` | — | Emit one structured result. |

### `dotbrain skills link` {#dotbrain-skills-link}

Reconcile selected skills in project or explicit global scope.

```text
dotbrain skills link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--scope` *text* | `project` | Delivery scope: project or global. |
| `--project` *text* | — | Select a named Brainspace. |
| `--repo` *path* | — | Select a wired checkout; defaults to the current checkout. |
| `--all` | — | Reconcile every registered project. |
| `--json` | — | Emit one structured result. |

### `dotbrain agents list` {#dotbrain-agents-list}

Discover locally available agents.

```text
dotbrain agents list [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--project` *text* | — | Show selections for a named Brainspace. |
| `--json` | — | Emit one structured result. |

### `dotbrain agents link` {#dotbrain-agents-link}

Reconcile selected agents in project or explicit global scope.

```text
dotbrain agents link [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--home` *path* | — | Override the private data root. |
| `--runtime` *text* | `all` | Filter runtimes: claude, codex, hermes, opencode, pi, cursor, or all. |
| `--scope` *text* | `project` | Delivery scope: project or global. |
| `--project` *text* | — | Select a named Brainspace. |
| `--repo` *path* | — | Select a wired checkout; defaults to the current checkout. |
| `--all` | — | Reconcile every registered project. |
| `--json` | — | Emit one structured result. |

## Beads

Manage the Beads tracker's state and backend. See [Beads backend](beads-backend.md).

### `dotbrain beads sync` {#dotbrain-beads-sync}

Sync declared local tracker bindings and pull configured remotes; never push.

```text
dotbrain beads sync [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project` *text* | — | Select a named Brainspace. |
| `--all` | — | Sync every registered project. |
| `--dry-run` | — | Preview tracker sync and configured pulls. |
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

## Exchange

Record the dotbrain home's changes and exchange them with its remote.

### `dotbrain sync` {#dotbrain-sync}

Record uncommitted home changes as sync commits, integrate the upstream, and push.

Acts on the whole home: one commit per changed Brainspace, then one home commit for the rest. A full sync then fetches and merges the upstream, keeping this machine's version of a file both sides changed and writing the other as NAME.sync-conflict-DATE-HOST.ext beside it (an edit wins over a delete). A push rejected because the remote moved is retried at most 3 times; sync never force-pushes. Files over sync.max-file-size in config.yaml (bytes, or a size such as 500KB or 1MB; default 1MB) stay uncommitted and are reported. If incoming changes would overwrite an uncommitted or ignored local file, Git refuses the merge; sync reports Git's diagnostic, pushes nothing, and fails. Offline, rejected, and remote-less homes exit 0 and keep the commits. Nested Git repositories are never recorded. Recording is refused during a merge, rebase, cherry-pick, or revert, with unmerged paths, or on a detached HEAD. Turn sync off with sync.enabled: false. Known limit: sync unstages everything before recording, so index-only state (partially staged hunks, git rm `--cached`, a staged mode change) is replaced by the working tree.

```text
dotbrain sync [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--push-only` | — | Record and push without fetching the remote. |
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

Sync the home (waiting at most 10 s), then emit a wired repo's Brain context. Fail-open.

```text
dotbrain hook session-start [ARGS]
```

| Argument | Description |
| --- | --- |
| `ARGS` | — |

### `dotbrain hook stop` {#dotbrain-hook-stop}

Start a detached push-only home sync and return at once. Fail-open and silent.

```text
dotbrain hook stop [ARGS]
```

| Argument | Description |
| --- | --- |
| `ARGS` | — |

### `dotbrain hook session-end` {#dotbrain-hook-session-end}

Start a detached full home sync and return at once. Fail-open and silent.

```text
dotbrain hook session-end [ARGS]
```

| Argument | Description |
| --- | --- |
| `ARGS` | — |

### `dotbrain hook run` {#dotbrain-hook-run}

Handle a session event for any runtime adapter, without reading a hook payload. Fail-open.

```text
dotbrain hook run [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--event` *choice* | — | Session event: startup, resume, clear, compaction, turn-end, or session-end. |
| `--checkout` *path* | — | Checkout the event belongs to. Default: the working directory. |
| `--format` *choice* | `text` | Context output: text (raw) or json (an additional_context object). |
