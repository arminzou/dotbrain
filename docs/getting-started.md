# Getting Started

This guide walks through the first local setup:

1. Install dotbrain and its machine prerequisites.
2. Bootstrap your global dotbrain home.
3. Wire one code repo to a private control root.
4. Verify the wiring and inspect the seeded config.

## Before You Start

- You need a local clone of this repo.
- By convention, dotbrain keeps private project state under `~/dotbrain`.
- The code repo you wire stays public or private on its own terms; dotbrain keeps Brain and execution
  state outside that repo.

## 1. Install dotbrain

From the dotbrain repo root:

```bash
./install.sh
```

The installer:

- installs `uv` if it is missing
- installs `bd` (Beads) if it is missing
- installs the `dotbrain` CLI from the local checkout

## 2. Bootstrap Your dotbrain Home

Run:

```bash
dotbrain bootstrap
```

This seeds your global dotbrain home with:

- `config.yaml`
- global agent hooks
- global skill links

## 3. Wire a Repo

Move to the code repo you want to wire and run:

```bash
dotbrain wire <repo>
```

Example:

```bash
dotbrain wire ~/repos/projects/my-app
```

Wiring creates or repairs a private control root for that project and connects the repo to it
through gitignored local links such as `.brain`, `.beads`, `.claude`, and `.codex`.

## 4. Verify the Result

If you update config or want to repair generated wiring later, run:

```bash
dotbrain refresh
```

For a read-only health check, run:

```bash
dotbrain doctor
```

At this point you should have:

- a seeded `~/dotbrain/config.yaml`
- a project control root under `~/dotbrain/projects/<name>/`
- local wiring in the repo that points at that control root

## 5. Edit Config Only When Needed

Most first-time setups can leave the default embedded beads mode alone.

When you do need configuration:

- use [configuration.md](/home/armin/repos/projects/dotbrain/docs/configuration.md) for
  `config.yaml` and `project.yaml`
- use [skills.md](/home/armin/repos/projects/dotbrain/docs/skills.md) for skill layering

## Next

- [architecture.md](/home/armin/repos/projects/dotbrain/docs/architecture.md) explains the control-root model.
- [cli-reference.md](/home/armin/repos/projects/dotbrain/docs/cli-reference.md) lists the public commands.
