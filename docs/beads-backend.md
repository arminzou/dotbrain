# Beads Backend

This page explains the two beads backend modes dotbrain supports, when to use each one, and how the
backend lifecycle fits into `load`, `migrate`, and cleanup commands.

## Two Modes

Per project, beads can run in one of two practical modes:

- `embedded`
  Local beads state lives in the project's private Brainspace.
- `server`
  The project uses a shared Dolt sql-server backend.

For most first-time setups, `embedded` is the right default.

## Embedded Mode

Use embedded mode when:

- the project is mostly local to one machine
- you do not need a shared sql-server backend
- you want the smallest operational footprint

In embedded mode, the Brainspace carries the local beads state and dotbrain can hydrate it
locally when needed.

## Server Mode

Use server mode when:

- the project should use a shared backend across machines or sessions
- you want multiple wired checkouts to connect to the same server-backed beads database
- the project has moved beyond the local embedded default

Server mode needs shared infrastructure defaults in `config.yaml`, typically under `beads.server`.
The per-project `project.yaml` then sets `beads.mode: server`.

See [configuration.md](/home/armin/repos/projects/dotbrain/docs/configuration.md) for the concrete
config examples.

## How dotbrain Decides

There are two layers of configuration:

- `~/dotbrain/config.yaml` for machine-wide server defaults
- `~/dotbrain/brainspaces/<name>/.brain/project.yaml` for per-project backend choice and overrides

In practice:

- if a project stays on the default path, it is usually `embedded`
- if a project declares `beads.mode: server`, dotbrain treats it as server-backed

## `dotbrain beads load`

Use `dotbrain beads load` to hydrate local beads state from the tracked declarations.

What it does depends on the backend:

- server-mode projects attach to the declared server tracker
- embedded projects initialize local beads state and pull it

This is a reconcile step for backend state. It does not touch repo wiring, hooks, or unrelated
workspace files.

## `dotbrain beads migrate`

Use `dotbrain beads migrate` when a project started as embedded and should move onto a remote
sql-server backend without losing its existing history.

Typical use case:

- a project began with the local embedded default
- later it needs a shared server backend
- you want to preserve existing beads history while moving to server mode

`migrate` is the transition step between those two worlds.

## `dotbrain beads drop-db`

`dotbrain beads drop-db` is a backend cleanup command for server-backed projects.

Use it only when you actually intend to remove the remote beads database. This is separate from
repo wiring and separate from `dotbrain unwire`.

Rule of thumb:

- `unwire` disconnects a repo from its Brainspace
- `drop-db` removes a server backend database

Those are different operations on purpose.

## Which One Should You Pick?

Choose `embedded` when you want the simplest default.

Choose `server` when the project genuinely needs shared backend infrastructure.

If you are unsure, start embedded and migrate later only when the project really needs the shared
server model.
