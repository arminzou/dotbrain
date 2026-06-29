---
name: build-context
description: Draft, rewrite, and normalize project-level AGENTS.md/CLAUDE.md context files at both the public repo and private .brain levels. Use when setting project agent instructions, making AGENTS.md canonical with CLAUDE.md symlinked to it at both levels, repairing context drift, bootstrapping .brain/CONTEXT.md, or keeping public AGENTS.md safe around private dotbrain wiring.
---

# Agent Context

## Overview

Use this skill when a user wants to set up or tune project-level agent-facing context files:
the repo `AGENTS.md`/`CLAUDE.md` and the private brain `.brain/AGENTS.md`/`.brain/CLAUDE.md`.

This skill is **brain-coupled** — it operates strictly within the current project. It never touches
workspace-root context files or anything outside the project tree.

The goal is to make the context hierarchy legible, complete, and low-drift:
- `AGENTS.md` canonical, `CLAUDE.md` symlinked at both levels
- brain `AGENTS.md` always bootstrapped from template
- `CONTEXT.md` present in the brain (bootstrapped if missing)
- public repo context safe for public consumption
- private operational detail kept behind `.brain/`

## When to Use

Use this skill when:
- the user asks to create, rewrite, or standardize `AGENTS.md` or `CLAUDE.md` in a project
- the user wants brain context bootstrapped or refreshed against the template
- a repo has both files as independent copies and drift is likely
- the user wants `.brain/CONTEXT.md` bootstrapped if it doesn't exist
- the public repo `AGENTS.md` needs to be kept safe around private dotbrain wiring

Don't use this skill for:
- authoring skill files (`SKILL.md`) — use `/skill-authoring`
- workspace-root context files (`~/AGENTS.md`, `~/CLAUDE.md`)
- product specs, ADRs, or user documentation that is not agent-facing
- one-off code comments or README cleanup
- deep refinement of `CONTEXT.md` terminology — seed initial terms here, then use `/grill-decisions` to stress-test and sharpen them

## Files This Skill Touches

| File | Purpose |
|------|---------|
| `<project>/AGENTS.md` | Repo-level context |
| `<project>/CLAUDE.md` | Symlink to `AGENTS.md` |
| `<project>/.brain/AGENTS.md` | Private brain-level context (source of truth) |
| `<project>/.brain/CLAUDE.md` | Symlink to `AGENTS.md` |
| `<project>/.brain/CONTEXT.md` | Domain vocabulary (bootstrapped if missing) |

Nothing outside the project tree is ever touched.

## Canonical Convention

- `AGENTS.md` is canonical at every level.
- `CLAUDE.md` is a symlink to `AGENTS.md` at every level.
- The nearest context file in the directory tree wins.
- Brain `.brain/AGENTS.md` overrides repo `AGENTS.md` when dotbrain is wired.

## Two-Level Structure

A dotbrain-wired project has two layers of agent context:

### Repo level (`AGENTS.md`)

- Tracked in git, visible to anyone who clones the repo.
- Self-contained: purpose, public paths, commands, verification, public hazards.
- Points to `.brain/AGENTS.md` as optional private context — missing is not an error.
- Must not expose private dotbrain internals (no `.brain/CONTEXT.md`, `.brain/adr/`,
  `.brain/project.yaml`, `.beads`, `bd` workflow, private issue tracker details).

### Private brain level (`.brain/AGENTS.md`)

- Never committed to the code repo — lives in the dotbrain brainspace.
- Holds private operational context: build/test commands, project-wide constraints,
  gotchas, tracker conventions, vocabulary/ADR/skill pointers.
- Bootstrapped from `templates/brain-AGENTS.md` — always refreshable against it.

## Working Process

### 1. Inspect current state

Check what exists at both levels:
```
ls -la AGENTS.md CLAUDE.md .brain/AGENTS.md .brain/CLAUDE.md .brain/CONTEXT.md
```
- Are `AGENTS.md` files regular files or symlinks?
- Are `CLAUDE.md` files symlinks?
- Does `.brain/CONTEXT.md` exist?

### 2. Update or create brain AGENTS.md

Always update `.brain/AGENTS.md` against `templates/brain-AGENTS.md`:
- If it exists, compare against the template — preserve user-authored content in
  the `## Project` section and any custom sections, but ensure the header and
  structural pointers are current.
- If it doesn't exist, create it from the template.
- Ensure `CLAUDE.md` is a symlink to `AGENTS.md` (replace with backup if regular).

### 3. Update or create repo AGENTS.md

Update `AGENTS.md` against `templates/project-AGENTS.md`:
- If it exists, preserve user-authored content (purpose, paths, commands, conventions,
  notes) while ensuring the private-context pointer and structure are current.
- If it doesn't exist, create it from the template.
- Scan for private dotbrain internals — none should appear. The only `.brain` path
  allowed is `.brain/AGENTS.md`.
- Ensure `CLAUDE.md` is a symlink to `AGENTS.md` (replace with backup if regular).

### 4. Bootstrap and populate CONTEXT.md

If `.brain/CONTEXT.md` does not exist, create it. Either way, seed or update minimal domain
terms based on what you observed while inspecting the project.

Scaffold (if creating from scratch):

```markdown
# CONTEXT.md

Domain vocabulary for this project. Terms here are canonical — use them consistently
in issues, plans, code, ADRs, and agent conversations.

## Terms

<!-- Populated by /build-context during project orientation. /grill-decisions will
     refine and stress-test these terms during planning sessions. -->
```

Seed terms from what you've already discovered during inspection — key concepts, domain
objects, non-obvious naming conventions, architecture patterns the project uses. Keep each
term brief (one line) and grounded in what's actually in the code or docs. Don't invent
terms the project doesn't use.

If `.brain/CONTEXT.md` already exists, review your observations against the current terms
and propose additions or refinements — but don't remove existing terms without asking.

Do not attempt deep terminology debates — that's `/grill-decisions` territory. The goal
here is to capture the obvious terms any orienting agent would notice, so the brain is
both complete and useful from the start.

### 5. Verify

- [ ] `readlink -f CLAUDE.md` resolves to `AGENTS.md` (repo level)
- [ ] `readlink -f .brain/CLAUDE.md` resolves to `.brain/AGENTS.md` (brain level)
- [ ] Reading through both paths at each level shows identical content
- [ ] Public `AGENTS.md` contains no private dotbrain internals beyond `.brain/AGENTS.md`
- [ ] Missing `.brain/AGENTS.md` is explicitly noted as non-fatal in the public file
- [ ] `.brain/CONTEXT.md` exists
- [ ] No workspace-root files were touched

## Repo-Level File Guidance

A repo-level `AGENTS.md` should include:
- Scope and override rules
- Private context pointer (`.brain/AGENTS.md` only)
- Project purpose and boundaries
- Important directory layout
- Working conventions
- Commands and verification steps
- Important notes and traps

If the repo is public, `AGENTS.md` must NOT include:
- Private dotbrain paths (`CONTEXT.md`, `adr/`, `project.yaml`, `docs/`)
- `.beads`, `bd` commands, or private execution workflow
- Private issue tracker details, roadmap, or domain vocabulary

## Brain-Level File Guidance

A brain `.brain/AGENTS.md` should include:
- The standard dotbrain bootstrap header (private context explanation,
  `DOTBRAIN.md` pointer)
- A `## Project` section with cross-cutting rules: build/test commands,
  project-wide constraints, gotchas, tracker conventions
- Pointers to `CONTEXT.md`, `adr/`, and `project.yaml`

The brain template is the canonical source for the header structure. User-authored
content lives primarily in the `## Project` section.

## CONTEXT.md Guidance

`CONTEXT.md` holds the domain vocabulary for the project. Terms defined there are
canonical — agents should use them consistently in issues, plans, code, and ADRs.

- This skill bootstraps the file if it doesn't exist, and seeds minimal terms based on
  what the agent observed while orienting in the project.
- Terms should be brief, grounded in actual code/docs, and limited to what's obvious
  from inspection — key concepts, domain objects, architecture patterns, non-obvious
  naming conventions.
- Deeper refinement belongs to `/grill-decisions`, which stress-tests and sharpens the
  vocabulary through debate. `/build-context` gives it something to start from.

## Common Pitfalls

1. **Leaving both `AGENTS.md` and `CLAUDE.md` as separate real files at either level.**
   That guarantees drift. Pick `AGENTS.md` as canonical and symlink `CLAUDE.md`.

2. **Exposing dotbrain internals in the public repo `AGENTS.md`.**
   Public tracked context must only mention `.brain/AGENTS.md`. No other `.brain`
   subpaths, no `.beads`, no `bd` workflow.

3. **Touching workspace-root files.**
   This skill is project-scoped. Never touch `~/AGENTS.md`, `~/CLAUDE.md`, or any
   other root-level context file.

4. **Replacing `CLAUDE.md` without a backup.**
   If it was a regular file with useful content, preserve it first as `.bak`.

5. **Over-populating CONTEXT.md with speculative terms.**
   Seed terms you actually observed in the code/docs — don't invent vocabulary the
   project doesn't use. Leave deep refinement to `/grill-decisions`.

6. **Forgetting the two-level structure.**
   Both the repo level and the private brain level need maintenance.
   Updating one without the other leaves the hierarchy incomplete.

7. **Writing generic filler instead of actionable context.**
   Agent context should explain navigation, conventions, workflows, and hazards.

## Verification Checklist

- [ ] Existing `AGENTS.md` and `CLAUDE.md` were inspected at BOTH levels before editing
- [ ] Brain `AGENTS.md` is current against `templates/brain-AGENTS.md`
- [ ] Repo `AGENTS.md` is current against `templates/project-AGENTS.md`
- [ ] `CLAUDE.md` is a symlink to `AGENTS.md` at each level
- [ ] `readlink -f CLAUDE.md` resolves correctly at each level
- [ ] Public `AGENTS.md` scanned for private dotbrain internals — only `.brain/AGENTS.md` allowed
- [ ] Missing `.brain/AGENTS.md` is explicitly non-fatal in public file
- [ ] `.brain/CONTEXT.md` exists (bootstrapped if it was missing)
- [ ] No workspace-root files were touched
- [ ] User-authored content was preserved in `## Project` and custom sections

## Templates

- `templates/brain-AGENTS.md` — brain-level AGENTS.md (private, source of truth)
- `templates/project-AGENTS.md` — repo-level AGENTS.md
