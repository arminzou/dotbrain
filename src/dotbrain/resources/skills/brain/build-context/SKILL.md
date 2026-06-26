---
name: build-context
description: Draft, rewrite, and normalize AGENTS.md/CLAUDE.md context files for repos and workspace roots, including public repos wired to private dotbrain context. Use when setting agent instructions, defining root-vs-local context boundaries, making AGENTS.md canonical with CLAUDE.md symlinked to it, repairing agent instruction drift, or keeping public AGENTS.md files safe around private dotbrain wiring.
---

# Agent Context

## Overview

Use this skill when a user wants to set up or tune agent-facing context files such as `AGENTS.md` and `CLAUDE.md`.

The goal is to make the context hierarchy legible and low-drift:
- one canonical file per directory (`AGENTS.md`)
- `CLAUDE.md` symlinked to it when both names are needed
- root context kept high-level
- project-specific operational detail pushed down into the nearest local context file

## When to Use

Use this skill when:
- the user asks to create, rewrite, or standardize `AGENTS.md` or `CLAUDE.md`
- the user wants root/workspace context separated from project-local instructions
- a repo has both files as independent copies and drift is likely
- you need to define directory layout, conventions, and cross-cutting notes for agents

Don't use this skill for:
- authoring skill files (`SKILL.md`)
- product specs, ADRs, or user documentation that is not agent-facing
- one-off code comments or README cleanup

## Canonical Convention

Default convention unless the user says otherwise:
- `AGENTS.md` is canonical
- `CLAUDE.md` is a symlink to `AGENTS.md`
- the nearest context file in the current directory tree wins
- the root context is a fallback, not the place for detailed project operations

## Dotbrain Public-Repo Convention

Some repos are public adopter repos wired locally to private dotbrain state through ignored `.brain`,
`.beads`, `.claude`, and `.codex` symlinks. The tracked public `AGENTS.md` must still work when a
fresh clone is not wired.

For a public or potentially public adopter repo:
- Keep the tracked `AGENTS.md` self-contained for normal source work: purpose, public paths,
  commands, verification, and public hazards.
- Add only one private-context pointer: if `.brain/AGENTS.md` exists locally, read it before
  substantial agent work for private project operations.
- State that missing `.brain/AGENTS.md` is not an error on unwired checkouts.
- Do not expose private dotbrain internals in the public file: no `.brain/CONTEXT.md`,
  `.brain/adr/`, `.brain/docs/*`, `.brain/project.yaml`, `.beads`, `bd` workflow, private issue
  tracker details, private roadmap, or private domain vocabulary paths.
- Do not create tracked public replacement files for missing private dotbrain state.

For private Brainspaces or private repos, it is fine to document the private paths directly when
they are part of the repo's durable operational context.

## Working Process

1. Inspect current state.
   - Check whether `AGENTS.md` and/or `CLAUDE.md` already exist.
   - Check whether either is already a symlink.
   - Read both before deciding what to keep, merge, or drop.
   - If working at a workspace root, inspect top-level directory layout before drafting content.

2. Decide scope.
   - Root/workspace-level files should contain only shared, cross-cutting guidance.
   - Project-local files should contain structure, workflows, commands, traps, and operational notes for that project.
   - Push detail downward instead of bloating the root file.
   - In public adopter repos, push private project operations behind the optional `.brain/AGENTS.md`
     pointer instead of listing private dotbrain paths in the tracked public context.

3. Clarify contents when the desired scope is not obvious.
   - If it is not clear what the user wants included in the context file, ask explicitly before drafting.
   - Ask what categories of information they want captured (for example: directory layout, commands, workflows, conventions, architecture notes, safety warnings, important paths, or excluded topics).
   - Do not guess missing content just because a nearby file or repo suggests a pattern.
   - If the user already stated a clear preference, follow it directly instead of re-asking.

4. Draft the file around agent needs, not human marketing.
   Keep it focused on:
   - scope and override rules
   - directory layout
   - organization conventions
   - important locations
   - cross-cutting safety notes

5. Preserve useful content, remove drift-prone duplication.
   - Merge useful facts from existing `CLAUDE.md` or old `AGENTS.md` into the new canonical file.
   - Remove project-specific detail from a root file if it belongs in a nearer context.
   - Avoid duplicating the same instructions at multiple levels unless repetition is intentionally defensive.
   - When migrating an old public convention into dotbrain, remove stale tracked references to the
     old private/project-operations paths after the durable content has been moved behind dotbrain.

6. Normalize the files.
   - Write or update `AGENTS.md`.
   - Before replacing an existing regular `CLAUDE.md`, make a backup such as `CLAUDE.md.bak`.
   - Replace `CLAUDE.md` with a symlink to `AGENTS.md`.
   - If the repo already has an `## Agent skills` block that points at private `.brain/` files, verify those files actually exist afterward. If they were missing or accidentally deleted, restore or recreate them instead of leaving broken references.

7. Verify.
   - Confirm `CLAUDE.md` resolves to `AGENTS.md`.
   - Read through the symlinked path to ensure content matches.
   - For public adopter repos, scan the tracked `AGENTS.md`/`CLAUDE.md` for private dotbrain
     internals. The only `.brain` path exposed publicly should normally be `.brain/AGENTS.md`.
   - Check that the resulting file stays concise and scope-appropriate.
   - For config/runtime repos, verify the context distinguishes durable source-of-truth files from volatile/generated runtime state so agents do not casually edit the wrong thing.
   - If the workspace root lives through a symlinked or synced path (for example `/home/...` resolving to `/mnt/...`), treat that as expected as long as `CLAUDE.md` still resolves to the correct canonical `AGENTS.md` content.

## Root File Guidance

A root `AGENTS.md` should usually include:
- what scope the root file covers
- that nearer local context overrides it
- top-level directory layout (e.g. code repos, infra, and notes, plus hidden config dirs like `~/.config`, `~/.claude`, `~/.codex`, `~/.ssh`, etc.)
- conventions for where code, notes, infra, and runtime state belong
- cross-cutting cautions about broad system changes

A root `AGENTS.md` should usually avoid:
- detailed service inventories
- long command cheat-sheets
- project-specific workflows
- operational detail that already has a natural home in a subdirectory context

If the user says the root file should stay high-level, take that literally. Push infra/service details down into the nearest relevant repo context instead of keeping them in the workspace root.

Important: "push detail down" does not mean delete useful detail. When a root file contains valuable operational specifics that should still live inside the repo, relocate them into one of these homes:
- the nearest local `AGENTS.md` for repeated directory-specific workflow
- a durable repo doc under `.brain/` for long-form reference or runbook material
- an existing conceptual/source-of-truth file such as `CONTEXT.md` when the detail is about domain language rather than workflow

A good rewrite preserves value while improving placement.

## Project-Local File Guidance

A project-local `AGENTS.md` should usually include:
- repo purpose and boundaries
- important directories and file ownership
- local commands, test/build workflows, and verification steps
- architecture or domain notes that matter repeatedly
- sharp edges, conventions, and non-obvious traps

For a public project-local `AGENTS.md` in a dotbrain-wired repo, keep private operational detail out
of this list and use the optional `.brain/AGENTS.md` pointer described above.

## Common Pitfalls

1. Leaving both `AGENTS.md` and `CLAUDE.md` as separate real files.
   That guarantees drift. Pick one canonical source and symlink the other.

2. Treating the root file like a dumping ground.
   If the detail only matters inside a single infra or service repo, move it there.

3. Replacing `CLAUDE.md` without a backup.
   If it was a real file with useful content, preserve it first.

4. Writing generic filler instead of actionable context.
   Agent context should explain navigation, conventions, workflows, and hazards.

5. Forgetting override rules.
   State clearly that the nearest local context file takes precedence.

6. Guessing what the user wants in the file when they have not been specific.
   If the desired contents are unclear, ask what should be included or excluded instead of inventing a structure from habit.

7. Exposing dotbrain internals in a public repo.
   Public tracked context should not mention private `.brain` subpaths, `.beads`, `bd`, private
   issue trackers, private roadmap paths, or private skill config. Point to `.brain/AGENTS.md` only
   and make that pointer optional for unwired clones.

## Verification Checklist

- [ ] Existing `AGENTS.md` and `CLAUDE.md` were inspected before editing
- [ ] Canonical file chosen explicitly (`AGENTS.md` by default)
- [ ] If the desired file contents were unclear, the user was asked what to include or exclude before drafting
- [ ] Root file content is high-level and cross-cutting only
- [ ] Project-specific detail lives in the nearest relevant local context file
- [ ] Existing `CLAUDE.md` was backed up before replacement if it was a regular file
- [ ] `CLAUDE.md` is now a symlink to `AGENTS.md`
- [ ] `readlink -f CLAUDE.md` resolves to `AGENTS.md`
- [ ] Reading through both paths shows identical content
- [ ] In public dotbrain-wired repos, the only public private-context path is `.brain/AGENTS.md`
- [ ] In public dotbrain-wired repos, missing `.brain/AGENTS.md` is explicitly non-fatal

## References

- See `references/root-context-pattern.md` for a concise root-level pattern derived from this workspace.
- See `templates/root-AGENTS.md` for a starter root context template.
- See `templates/project-AGENTS.md` for a starter project-local template.
