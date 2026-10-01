# Beads Backend

Dotbrain keeps each project's plans and tasks in [Beads](https://github.com/gastownhall/beads)
(`bd`), a dependency-aware issue tracker built on Dolt. This page covers the backend modes, how to
choose one, and the commands that manage them.

## Modes

| | `embedded` (default) | `server` | `none` |
| --- | --- | --- | --- |
| Where state lives | A local Dolt store in the Brainspace | A shared Dolt sql-server | Nowhere |
| Sync across machines | Optional, through a Dolt remote | Live | n/a |
| Setup | None | `beads.server` in `config.yaml` | None |
| Good for | Most projects | Several machines working at once | Projects tracked elsewhere, such as GitHub Issues |

```mermaid
flowchart LR
  accTitle: Embedded and server Beads modes
  subgraph emb["embedded"]
    c1["checkout"] --> s1[("`**Brainspace**
  *.beads/*`")]
    s1 -. "push / pull" .-> r1[("Dolt remote")]
  end
  subgraph srv["server"]
    c2["machine A"] --> d[("Dolt sql-server")]
    c3["machine B"] --> d
  end
```

If you are unsure, start `embedded`. Moving to `server` later keeps history.

## How Dotbrain Decides

Two files are involved:

- `~/dotbrain/config.yaml` holds machine-wide server defaults under `beads.server`.
- `.brain/project.yaml` picks the mode per project with `beads.mode`. Leaving it out means
  `embedded`.

```yaml
# .brain/project.yaml
beads:
  mode: server
  database: my_app_beads   # optional; defaults to the project name
```

See [Configuration](configuration.md) for the full shape.

## Server Mode

Point `config.yaml` at your sql-server once per machine:

```yaml
# ~/dotbrain/config.yaml
beads:
  server:
    host: db.example.internal
    port: 3307
    user: beads
    ssh_host: bastion.example.internal   # optional SSH hop, used by drop-db
```

::: warning
Never put passwords or tokens in `config.yaml`. Keep credentials in your secrets store.
:::

Then set `beads.mode: server` in the project and run `dotbrain wire` or `dotbrain beads load`.

## Commands

### `beads load`

Hydrates local tracker state from the declarations: attaches server trackers, initializes embedded
ones, then pulls. It only pulls; it never pushes and never touches links or hooks.

```bash
dotbrain beads load --dry-run    # preview
dotbrain beads load              # the current repo's project
dotbrain beads load --all        # every Brainspace that uses beads
```

Run it on a fresh machine after cloning your dotbrain home.

### `beads migrate`

Moves an embedded tracker onto the sql-server with its history.

```mermaid
flowchart LR
  accTitle: Migrating an embedded tracker to a server
  e[("`**Embedded**
  Brainspace *.beads/*`")] -- "dotbrain beads migrate" --> s[("`**Server**
  Dolt sql-server`")]
```

```bash
dotbrain beads migrate --dry-run   # print the planned bd sequence
dotbrain beads migrate             # the current repo's project
dotbrain beads migrate --all       # every embedded Brainspace
```

### Cleaning Up

`dotbrain beads list-db` lists the databases on the server. `dotbrain beads drop-db` removes one.

::: danger
`drop-db` deletes the remote database and every issue in it. It is separate from `dotbrain unwire`
on purpose: `unwire` disconnects a repo, `drop-db` destroys tracker data.
:::

## Working With the Tracker

Agents drive Beads through the `operate-execution` skill, but you can use `bd` directly in any wired
repo:

```bash
bd ready              # issues with no open blockers
bd show <id>          # one issue with its dependencies
bd list --status open
```
