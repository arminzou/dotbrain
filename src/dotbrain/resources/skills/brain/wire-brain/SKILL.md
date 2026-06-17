---
name: wire-brain
description: Wire a repo into dotbrain by creating or updating its control root, Brain, agent workspace symlinks, beads pointer, and repo agent instructions. Use when starting a new project under dotbrain, connecting an existing repo to a control root, repairing .brain/.beads/.claude/.codex wiring, or updating bootstrap expectations.
---

# Wire Brain

Connect a code repo to its project control root in dotbrain.

## Preconditions

- dotbrain is available at `~/dotbrain`.
- The target code repo path is known.
- The project name defaults to the repo directory name unless the user specifies one.
- `dotbrain bootstrap` performs machine-wide reconciliation later; this skill handles one target
  repo/control root at a time.
- Wiring makes one minimal tracked adopter-repo change: a context pointer to
  `.brain/AGENTS.md`. Do not edit `.gitignore`, `README.md`, `dev/`, docs, source, or legacy
  context as part of wiring.

## Default Command

From the project repo, run:

```bash
dotbrain wire
```

Use `--repo <path>` or `--name <project-name>` only when the defaults are wrong.

To connect GitHub public intake at wire time, add `--github <org>/<repo>`; it writes
`agents/issue-tracker.md` in the connected state. The default is private-only (beads is always the
source of truth).

The script owns deterministic wiring and appends the `.brain/AGENTS.md` pointer idempotently to the
repo's `AGENTS.md` and, when distinct, `CLAUDE.md`. Use the rest of this skill to inspect results,
repair edge cases, or make explicit follow-up changes after the user approves them.

## Control Root Layout

Create or update `~/dotbrain/projects/<name>/`:

```text
.brain/
  AGENTS.md       # Brain entrypoint and read order
  CLAUDE.md -> AGENTS.md
  CONTEXT.md     # domain vocabulary, created lazily when useful
  adr/           # decisions, created lazily
  agents/        # skill config (skills.yaml) and issue-tracker.md, CLI-seeded from templates/brain/
  docs/          # optional durable operational docs
.beads/          # execution engine: thin beads pointer/config plus ignored runtime state
.claude/         # Claude workspace: SessionStart hook (brain + `bd prime`)
.codex/          # Codex workspace: brain + beads `bd codex-hook` hooks
```

Do not create a per-project brain git repo. The control root is versioned as part of dotbrain.

## Steps

1. **Create or inspect the brain.**
   - Read any existing `.brain/` files before changing them.
   - Seed `.brain/AGENTS.md` with read order: agent instructions, `bd ready` / `bd list`, system
     docs, `CONTEXT.md`, then ADRs.
   - Create `.brain/CONTEXT.md` and `.brain/adr/` only when there is real content.

2. **Initialize beads for the control root.**
   - Use the current bootstrap policy for `.beads/config.yaml` and the named database.
   - Verify with `bd -C <repo> ready` after the repo symlink is wired, or
     `bd -C ~/dotbrain/projects/<name> ready` while operating directly in dotbrain.
   - Dolt/runtime state stays ignored. `dotbrain wire` owns the commit: it undoes beads' own
     `bd init` commit and lands the whole control root as one `feat(brain): wire <name>` commit in
     dotbrain (wire-project owns control-root writes). Do not hand-commit the
     dotbrain side.

3. **Wire the repo symlinks.**
   ```bash
   ln -s ~/dotbrain/projects/<name>/.brain  <repo>/.brain
   ln -s ~/dotbrain/projects/<name>/.beads  <repo>/.beads
   ln -s ~/dotbrain/projects/<name>/.claude <repo>/.claude
   ln -s ~/dotbrain/projects/<name>/.codex  <repo>/.codex
   ```
   Add `/.brain`, `/.beads`, `/.claude`, and `/.codex` to `<repo>/.git/info/exclude` with leading
   slashes and no trailing slashes. Any symlink whose target is outside the containing git repo is
   local wiring and must be ignored, not tracked. Do not edit the adopter repo's tracked
   `.gitignore` as part of wiring. Exception: the dotbrain repo itself tracks its project #0
   symlink ignore policy in `.gitignore`.

4. **Let the CLI scaffold `.brain/agents/`.**
   `dotbrain wire` seeds `agents/` from `templates/brain/`: a `skills.yaml` baseline plus
   an `issue-tracker.md` stub. `--github <org>/<repo>` sets the `GitHub intake:` key in that stub.
   This skill provisions the containers; it does not hand-write `agents/` content.
   - `agents/labels.md` is **not** seeded — `operate-beads` / `triage-public` create it the first
     time a label convention is actually decided. An absent file means the canonical triage defaults.
   - Brain `AGENTS.md` guidance (read `CONTEXT.md`, use the glossary, flag ADR conflicts) ships in
     the template stub, not a per-project `domain.md`.

5. **Add only the adopter repo context pointer.**
   Append the one-line `.brain/AGENTS.md` pointer to the repo's tracked `AGENTS.md` and, if it is a
   distinct file, `CLAUDE.md`. Do not rewrite or consolidate the repo context during wiring. If the
   user later asks to consolidate repo context, use `build-context` as a separate, explicit
   follow-up.

## Done When

- `<repo>/.brain` resolves to `~/dotbrain/projects/<name>/.brain`.
- `<repo>/.beads` resolves to `~/dotbrain/projects/<name>/.beads`.
- `<repo>/.claude` resolves to `~/dotbrain/projects/<name>/.claude`.
- `<repo>/.codex` resolves to `~/dotbrain/projects/<name>/.codex`.
- `<repo>/.git/info/exclude` ignores `/.brain`, `/.beads`, `/.claude`, and `/.codex`.
- No symlink pointing outside `<repo>` is tracked by git.
- `bd -C <repo> ready` works or reports a valid empty database.
- `.brain/agents/` carries the CLI-seeded `skills.yaml` baseline and `issue-tracker.md` stub.
- The repo's agent context has a one-line pointer to `.brain/AGENTS.md`.
- `git -C <repo> status --short` shows no tracked-file changes other than that pointer.

Brain knowledge writes are agent-managed (the brain is git-tracked, so changes are revertable). Execution-state writes in beads are agent-managed too.
