# Wiring

This page covers the wiring model behind dotbrain: what gets connected, what stays private, and
when to use `wire`, `refresh`, or `unwire`.

For the first-run setup, start with
[getting-started.md](/home/armin/repos/projects/dotbrain/docs/getting-started.md).

## What Wiring Means

Wiring connects a code repo to a private Brainspace under your dotbrain data root.

The repo gets local, gitignored wiring entries such as:

- `.brain`
- `.beads`
- `.claude`
- `.codex`

`.brain` and `.beads` point at the private Brainspace; `.claude` and `.codex` are real project
directories containing individually ignored dotbrain resource links. The Brainspace typically lives
under `~/dotbrain/brainspaces/<name>/`.
An existing `~/dotbrain/projects/<name>/` layout (the pre-rename name) is still recognized; new
Brainspaces are created under `brainspaces/`.

The important boundary is:

- the code repo stays the code repo
- the Brain, execution state, and agent workspace state live outside it

## What `dotbrain wire` Does

Use `dotbrain wire` when you are connecting a repo to dotbrain for the first time, or when the
repo and Brainspace should be reconciled again from the source of truth.

Typical usage:

```bash
dotbrain wire <repo>
```

This creates or repairs:

- the private Brainspace
- the repo-root wiring links
- seeded project config such as `project.yaml`
- local agent workspace wiring for supported agents

## What `dotbrain refresh` Does

Use `dotbrain refresh` when the project is already wired and you want to repair or resync the
generated local state without treating it like a fresh connect.

Typical usage:

```bash
dotbrain refresh
```

Use `refresh` after changes like:

- updating project config
- updating shared dotbrain-managed files
- fixing missing local links or workspace files
- pulling the latest execution state into a wired checkout

Rule of thumb:

- use `wire` to connect or re-connect a project
- use `refresh` to repair or resync an already wired project

## What `dotbrain unwire` Does

Use `dotbrain unwire` when a repo should no longer point at a Brainspace.

Typical usage:

```bash
dotbrain unwire
```

`unwire` disconnects the adopter repo from its Brainspace. Depending on the flags you choose, the
Brainspace can be kept, archived, or deleted.

Important detail:

- `unwire` is about repo/Brainspace disconnection
- remote beads database cleanup is separate

If a project uses a server beads backend, dropping that remote database is a separate operation.

## Worktrees

Worktrees do not get separate Brains or separate execution stores.

They reuse the main checkout's Brain and execution store through:

- `.brain`
- `.beads`

When either link is absent, invoke the `wire-worktree` skill. It derives the main checkout from Git
and creates only those links.

## Troubleshooting

Common wiring problems are usually one of these:

- missing local links
- links pointing at the wrong Brainspace
- a repo that was cloned fresh and never wired
- a worktree missing its `.brain` or `.beads` link

Start with:

```bash
dotbrain doctor
```

Then, if the repo should already be wired, run:

```bash
dotbrain refresh
```

If the project was never wired correctly or the repo/Brainspace relationship changed, run:

```bash
dotbrain wire <repo>
```

## Rule Of Thumb

Wiring is local machine plumbing. It should stay gitignored, private, and reversible.
