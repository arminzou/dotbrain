---
name: wire-brain
description: Wire, repair, refresh, or inspect a repo's dotbrain Brainspace using the current dotbrain CLI. Use when starting a project under dotbrain, attaching an existing repo to a Brainspace, repairing .brain/.beads/.claude/.codex links, reconciling skills/agents/hooks after an upgrade, or checking bootstrap expectations.
---

# Wire Brain

Connect an adopter repo to its private Brainspace through `dotbrain`. The CLI owns wiring,
scaffolding, symlink reconciliation, hooks, skill links, agent links, and beads setup. Agents using
this skill choose the right CLI command, inspect the result, and hand Brain content changes to the
skill that owns that content.

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
- `dotbrain bootstrap`: install or reconcile machine-global hooks and global skills.
- `dotbrain doctor`: inspect machine readiness, project wiring, hooks, and beads health.
- `dotbrain unwire`: detach an adopter repo and keep, archive, or delete the private Brainspace.

Do not recreate these steps by hand unless the CLI reports a concrete obstruction that must be
removed first.

## Ownership

`~/dotbrain/config.yaml` holds global infrastructure defaults, such as a shared beads sql-server.
Per-project identity lives in `~/dotbrain/brainspaces/<name>/.brain/project.yaml`:

- `beads.mode`: `embedded`, `server`, or `none`.
- `agents`: active workspaces, usually `claude` and/or `codex`.
- `skills`: project skill extras beyond the packaged required core.
- `subagents`: project subagent extras.
- `public-tracker` and `public-tracker-id`: public intake and contributor-collaboration metadata,
  never a mirror of private execution.

The CLI seeds missing Brain scaffolding and links runtime assets. Agents author Brain knowledge only
through the relevant Brain skills: context through `build-context`, execution through
`operate-execution`, design through `to-design`, and public intake through `triage-public`.

## Wiring Contract

A wired adopter repo points at its Brainspace through local, gitignored symlinks. Expected links are derived from project config:

- `.brain` always points at the Brain.
- `.beads` exists unless `beads.mode` is `none`.
- `.claude` exists when the `claude` agent workspace is active.
- `.codex` exists when the `codex` agent workspace is active.

The repo's `.git/info/exclude` ignores `/.brain`, `/.beads`, `/.claude`, and `/.codex`. The public
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

- Broken or missing repo symlinks for one project: `dotbrain wire --repo <path>`.
- Existing Brainspaces need repo link reconciliation: `dotbrain wire --all`.
- Skills, agents, hooks, templates, or legacy skill manifests changed: `dotbrain refresh --name
  <project>` or `dotbrain refresh --all`.
- Machine-global hooks or global skills are stale: `dotbrain bootstrap`, or `dotbrain bootstrap
  --only claude-hook`, `--only codex-hook`, or `--only skills`.
- Need a health report before deciding: `dotbrain doctor`.

`refresh` does not create projects. `wire --all` reconciles known Brainspaces and warns when it
cannot find an adopter repo.

## Worktrees

dotbrain worktree support reuses the main checkout's Brainspace links. Session-start hooks and the
worktree bootstrap commands repair worktree links so worker sessions see the same Brain, beads, and
agent workspaces as the main checkout.

Use the CLI entrypoints for worktree launches and bootstrap hooks. Do not create separate
Brainspaces for git worktrees.

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
- Expected `.beads`, `.claude`, and `.codex` links match `.brain/project.yaml`.
- `.git/info/exclude` contains the dotbrain link entries.
- `git -C <repo> status --short` shows no unexpected tracked changes.
- If beads are enabled, `bd -C <repo> ready` works or reports a valid empty tracker.
- Public repo files contain no private Brain content beyond the `.brain/AGENTS.md` pointer.
