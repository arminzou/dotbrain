---
name: wire-brain
description: Wires, repairs, refreshes, or inspects a repo's dotbrain Brainspace by driving the dotbrain CLI. Use when starting a project under dotbrain, attaching an existing repo to a Brainspace, repairing wiring in a main checkout or linked Git worktree, reconciling agent workspace resources after an upgrade, or checking bootstrap expectations.
---

# Wire Brain

Connect an adopter repo to its private Brainspace through `dotbrain`. The CLI owns wiring,
scaffolding, resource reconciliation, hooks, skill links, agent delivery, and beads setup. Agents using
this skill choose the right CLI command, inspect the result, and hand Brain content changes to the
skill that owns that content.

## Choose the wiring branch

For every checkout, check installation below, then choose a CLI command. When attaching or
repairing a linked Git worktree, read [Worktree attachment](references/worktree.md) for its shared
state and verification rules. `dotbrain wire` discovers the main checkout through Git metadata;
the CLI creates the worktree's wiring.

## First run

Before choosing a CLI command, check whether `dotbrain` is on `PATH`. If it is, continue without
installing anything.

If it is absent, this is a machine that has never run dotbrain — so resolve the dotbrain home
before installing anything.

### Ask before creating a dotbrain home

Check for the dotbrain home: `$DOTBRAIN_HOME` when set, otherwise `~/dotbrain`. If it already
exists, say nothing and move on to the installer.

If it does not exist, **stop and ask the operator** before creating one:

> No dotbrain home on this machine. Do you already have one in git? Give me the remote and I'll
> clone it. Otherwise I'll create a fresh one.

The home holds every Brainspace — the Brain, the work graph, the whole private history — and
it is normally a git repo the operator pushes somewhere. Creating a fresh one on a machine whose
operator already has a populated one elsewhere leaves them with an empty, diverged home, and they
usually do not find out until they notice their projects are missing. Nothing on the machine
distinguishes the two cases, so asking is the only way to tell them apart.

When they name a remote, clone it first, into that exact path:

```bash
git clone <remote> ~/dotbrain
```

Then run the installer. `dotbrain bootstrap` is idempotent: it seeds only the files the clone is
missing and leaves the existing git checkout alone.

### Install the CLI

Run the installer shipped beside this skill:

- On macOS or Linux: `${CLAUDE_PLUGIN_ROOT}/scripts/install.sh`.
- On Windows: `pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT/scripts/install.ps1"`.

The installer provides `uv`, `bd`, the CLI version pinned to this plugin release, and runs
`dotbrain bootstrap` — which creates and git-initializes the dotbrain home when it is absent. Then
resume this skill's normal wiring flow in the current repo.

## Command choice

Use the narrowest command that matches the symptom. `dotbrain --help` carries the current flags;
this table only carries the routing.

| Symptom or job | Command |
|---|---|
| Attach a main checkout or linked Git worktree | `dotbrain wire --repo <path>` |
| Repair an existing wired checkout | `dotbrain refresh` from that checkout |
| Brain-only project, no adopter repo | `dotbrain wire --project <project> --no-repo` |
| Existing Brainspaces need registered-checkout reconciliation | `dotbrain refresh --all` |
| Config, skills, agents, hooks, or templates changed | `dotbrain refresh --project <project>` / `--all` |
| Prepare machine-global resources | `dotbrain bootstrap` |
| Global skills or subagents are stale | `dotbrain skills link --scope global` / `dotbrain agents link --scope global` |
| Need a health report before deciding | `dotbrain doctor` |
| Detach a repo from its Brainspace | `dotbrain unwire` |

Project operations default to the current wired checkout, including a nested directory or
worktree. Outside it, use `--project <name>`; named selection respects the project's local checkout
override. `--all` selects registered projects and conflicts with individual selectors. `--home`
overrides the private data root. `refresh` maintains existing projects; it never creates one.

Do not recreate these steps by hand unless the CLI reports a concrete obstruction that must be
removed first.

## Ownership

`~/dotbrain/config.yaml` holds global infrastructure defaults, such as a shared beads sql-server.
Per-project identity lives in `~/dotbrain/brainspaces/<name>/.brain/project.yaml`:

- `beads.mode`: `embedded`, `server`, or `none`.
- `agents`: active workspaces, usually `claude` and/or `codex`.
- `skills`: project skill selection linked into the active workspaces.
- `subagents`: project subagent extras.
- `public-tracker` and `public-tracker-id`: public intake and contributor-collaboration metadata,
  never a mirror of private execution.

The CLI seeds missing Brain scaffolding and links runtime assets. Agents maintain Brain knowledge
through the relevant Brain skills: context health through `curate-project-context`, execution
through `manage-work-graph`, design through `to-design`, and public intake through
`triage-public`.

## Wiring contract

A wired adopter repo points at its Brainspace through local, gitignored symlinks and has real agent workspace directories. Expected wiring is derived from project config:

- `.brain` always points at the Brain.
- `.beads` exists unless `beads.mode` is `none`.
- `.claude` is a real directory when the `claude` agent workspace is active.
- `.codex` is a real directory when the `codex` agent workspace is active.

Skills and Claude agents use symlinks. Codex agent TOML definitions are generated real files with
the marker `# dotbrain-managed-agent: v1`; customize their source in the private home. Dotbrain
overwrites or prunes marked copies and preserves unmarked files and foreign links.

The Git exclusion file ignores `/.brain`, `/.beads`, and each workspace resource dotbrain creates. The public
repo context may contain the standard pointer to `.brain/AGENTS.md`; private Brain paths, ADRs,
beads details, and tracker operations stay out of public repo files.

## Wiring one repo

Run `dotbrain wire` from the adopter repo, or pass `--repo <path>` from elsewhere.

For initial main-checkout wiring, use `--project <project>` when the Brainspace name should differ
from the repo directory name. Existing checkouts and worktrees use their established identity.
Use beads options only for the initial tracker setup when project config or global config is not
already sufficient:

```bash
dotbrain wire --repo /path/to/repo --server-host db.example.internal
dotbrain wire --repo /path/to/repo --remote https://doltremoteapi.dolthub.com/owner/repo
dotbrain wire --repo /path/to/repo --skip-beads
```

After wiring, run:

```bash
dotbrain doctor
git -C /path/to/repo status --short
```

Expected public repo changes are limited to the agent context pointer when it is newly inserted.
Symlinks whose targets are outside the repo must remain untracked.

## Detachment

Detach through the CLI:

```bash
dotbrain unwire --repo /path/to/repo
```

Detachment removes the selected checkout's managed wiring and context pointer while keeping the
Brainspace, registration, user-owned workspace files, and other wired worktrees. Brainspace
archival or deletion is an operator-owned filesystem action. Remote database deletion remains
separate: use `dotbrain beads drop-db <database> --yes` only when explicitly requested.

## Verification

Before declaring wiring fixed:

- `dotbrain doctor` reports no relevant errors.
- `readlink <repo>/.brain` resolves into `~/dotbrain/brainspaces/<name>/.brain`.
- Expected `.beads` links and materialized `.claude` / `.codex` workspaces match `.brain/project.yaml`.
- Git's exclusion file contains the dotbrain-managed entries (`git rev-parse --git-path info/exclude`).
- `git -C <repo> status --short` shows no unexpected tracked changes.
- If beads are enabled, `bd -C <repo> ready` works or reports a valid empty tracker.
- Public repo files contain no private Brain content beyond the `.brain/AGENTS.md` pointer.
