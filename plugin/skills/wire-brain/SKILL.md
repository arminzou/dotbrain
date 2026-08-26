---
name: wire-brain
description: Wire, repair, refresh, or inspect a repo's dotbrain Brainspace using the current dotbrain CLI. Use when starting a project under dotbrain, attaching an existing repo to a Brainspace, repairing .brain/.beads links, reconciling agent workspace resources after an upgrade, or checking bootstrap expectations.
---

# Wire Brain

Connect an adopter repo to its private Brainspace through `dotbrain`. The CLI owns wiring,
scaffolding, symlink reconciliation, hooks, skill links, agent links, and beads setup. Agents using
this skill choose the right CLI command, inspect the result, and hand Brain content changes to the
skill that owns that content.

## First Run

Before choosing a CLI command, check whether `dotbrain` is on `PATH`. If it is, continue without
installing anything. If it is absent, run the installer shipped beside this skill:

- On macOS or Linux: `${CLAUDE_PLUGIN_ROOT}/scripts/install.sh`.
- On Windows: `pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT/scripts/install.ps1"`.

The installer provides `uv`, `bd`, the CLI version pinned to this plugin release, and runs
`dotbrain bootstrap`. Then resume this skill's normal wiring flow in the current repo.

## Command Choice

Use the narrowest command that matches the job:

- `dotbrain wire --repo <path>`: create or repair one Brainspace and attach one adopter repo.
- `dotbrain wire --name <project> --no-repo`: create a Brain-only Brainspace.
- `dotbrain wire --all`: reconcile every existing Brainspace with its adopter repo under the repo
  base.
- `dotbrain refresh`: refresh an existing Brainspace; use `--name <project>` to select one project.
- `dotbrain refresh --name <project>`: refresh one existing Brainspace after config, skill, agent,
  template, or CLI changes.
- `dotbrain refresh --all`: refresh every Brainspace without creating new projects.
- `dotbrain bootstrap`: reconcile global skills and subagents.
- `dotbrain doctor`: inspect machine readiness, project wiring, and beads health.
- `dotbrain unwire`: detach an adopter repo and keep, archive, or delete the private Brainspace.

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

The CLI seeds missing Brain scaffolding and links runtime assets. Agents author Brain knowledge only
through the relevant Brain skills: context through `build-context`, execution through
`operate-execution`, design through `to-design`, and public intake through `triage-public`.

## Wiring Contract

A wired adopter repo points at its Brainspace through local, gitignored symlinks and has real agent workspace directories. Expected wiring is derived from project config:

- `.brain` always points at the Brain.
- `.beads` exists unless `beads.mode` is `none`.
- `.claude` is a real directory when the `claude` agent workspace is active.
- `.codex` is a real directory when the `codex` agent workspace is active.

The repo's `.git/info/exclude` ignores `/.brain`, `/.beads`, and each workspace link dotbrain creates. The public
repo context may contain the standard pointer to `.brain/AGENTS.md`; private Brain paths, ADRs,
beads details, and tracker operations stay out of public repo files.

## Wire One Repo

From the adopter repo, run:

```bash
dotbrain wire
```

From elsewhere, pass the repo explicitly:

```bash
dotbrain wire --repo /path/to/repo
```

Use `--name <project>` only when the Brainspace name should differ from the repo directory name.
Use beads options only for the initial tracker setup when project config or global config is not
already sufficient:

```bash
dotbrain wire --repo /path/to/repo --beads-server-host db.example.internal
dotbrain wire --repo /path/to/repo --beads-remote https://doltremoteapi.dolthub.com/owner/repo
dotbrain wire --repo /path/to/repo --skip-beads
```

After wiring, run:

```bash
dotbrain doctor
git -C /path/to/repo status --short
```

Expected public repo changes are limited to the agent context pointer when it is newly inserted.
Symlinks whose targets are outside the repo must remain untracked.

## Repair Or Refresh

Use repair commands by symptom:

- Broken or missing symlinks in the main checkout: `dotbrain wire --repo <path>`.
- Broken or missing `.brain` or `.beads` in a git worktree: invoke `wire-worktree`.
- Existing Brainspaces need repo link reconciliation: `dotbrain wire --all`.
- Skills, agents, hooks, templates, or legacy skill manifests changed: `dotbrain refresh --name
  <project>` or `dotbrain refresh --all`.
- Global skills or subagents are stale: `dotbrain bootstrap` or `dotbrain bootstrap --only skills`.
- Need a health report before deciding: `dotbrain doctor`.

`refresh` does not create projects. `wire --all` reconciles known Brainspaces and warns when it
cannot find an adopter repo.

## Worktrees

dotbrain does not manage worktree creation or repair. In a worktree without `.brain` or `.beads`,
invoke the plugin-delivered `wire-worktree` skill. It derives the main checkout from Git and creates
only those two links. Use `dotbrain wire` only for adopter-repo/Brainspace wiring.

## Offboarding

Detach through the CLI:

```bash
dotbrain unwire --repo /path/to/repo
dotbrain unwire --repo /path/to/repo --archive
dotbrain unwire --repo /path/to/repo --delete
dotbrain unwire --name <project> --no-repo --archive
```

Remote beads databases are separate from Brainspace offboarding. Use `dotbrain beads drop-db` only
when the operator explicitly wants to remove the server-side database.

## Verification

Before declaring wiring fixed:

- `dotbrain doctor` reports no relevant errors.
- `readlink <repo>/.brain` resolves into `~/dotbrain/brainspaces/<name>/.brain`.
- Expected `.beads` links and materialized `.claude` / `.codex` workspaces match `.brain/project.yaml`.
- `.git/info/exclude` contains the dotbrain link entries.
- `git -C <repo> status --short` shows no unexpected tracked changes.
- If beads are enabled, `bd -C <repo> ready` works or reports a valid empty tracker.
- Public repo files contain no private Brain content beyond the `.brain/AGENTS.md` pointer.
