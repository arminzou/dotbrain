---
name: build-context
description: Draft, rewrite, and normalize project-level AGENTS.md/CLAUDE.md context files at both the public repo and private .brain levels. Use when setting project agent instructions, making AGENTS.md canonical with CLAUDE.md symlinked to it at both levels, repairing context drift, or keeping public AGENTS.md safe around private dotbrain wiring.
---

# Build Context

Maintain a project's agent-facing context files so the hierarchy is legible and low-drift. A wired
project has two levels, and both need maintenance:

| Level | File | Holds |
|---|---|---|
| Repo | `AGENTS.md` | Public: purpose, layout, commands, verification, hazards |
| Brain | `.brain/AGENTS.md` | Private: build/test detail, constraints, gotchas, tracker conventions, canon pointers |

At each level `AGENTS.md` is canonical and `CLAUDE.md` is a symlink to it. The nearest context file
in the tree wins, so `.brain/AGENTS.md` overrides the repo file when dotbrain is wired.

This skill is project-scoped: it works inside the current project tree and leaves workspace-root
files (`~/AGENTS.md`, `~/CLAUDE.md`) alone.

## Boundaries

- **vs `write-skills`**: that authors `SKILL.md` files; this authors project context.
- **vs `grill-decisions`**: that owns how vocabulary is settled. This reads `CONTEXT.md` to phrase
  things accurately and never writes it. Other skills may add a term once it is settled;
  `grill-decisions` is where a contested or fuzzy one gets resolved.
- Product specs, ADRs, user documentation, and README cleanup are outside this skill.

## Process

### 1. Inspect both levels

```bash
ls -la AGENTS.md CLAUDE.md .brain/AGENTS.md .brain/CLAUDE.md .brain/CONTEXT.md
```

Note which files exist, which are regular files, and which are already symlinks.

Completion: you can state the current shape at both levels, including which `CLAUDE.md` files are
real files that need converting.

### 2. Read CONTEXT.md if present

Domain terms there inform accurate phrasing in both files. Absence is a legitimate state: note that
`grill-decisions` populates vocabulary, and move on without creating the file.

Completion: either the vocabulary is loaded, or its absence is noted for the user.

### 3. Write the brain AGENTS.md

Bring `.brain/AGENTS.md` up to date against `templates/brain-AGENTS.md`, creating it from the
template if absent. Preserve user-authored content, which lives mostly in the `## Project` section;
refresh the header and the structural pointers to `CONTEXT.md`, `adr/`, and `project.yaml`.

Completion: the file matches the template's structure and every user-authored section survived.

### 4. Write the repo AGENTS.md

Bring `AGENTS.md` up to date against `templates/project-AGENTS.md`, creating it from the template if
absent. Preserve user-authored purpose, paths, commands, conventions, and notes.

Where the repo is public, the file stays safe for public consumption: the one permitted `.brain`
reference is the pointer to `.brain/AGENTS.md`, marked as optional so a missing Brain is not an
error. Keep private paths (`CONTEXT.md`, `adr/`, `project.yaml`, `docs/`), `.beads`, `bd` workflow,
tracker details, and domain vocabulary out of it.

If the user supplied `/init` output, absorb it as a draft into the template structure rather than
letting it own the file.

Completion: every heading is filled from real project knowledge rather than filler, and a scan for
private paths returns only the `.brain/AGENTS.md` pointer.

### 5. Converge the symlinks

At each level, make `CLAUDE.md` a symlink to `AGENTS.md`. Where `CLAUDE.md` is a regular file with
content worth keeping, save it as `.bak` before replacing it.

Completion: `readlink -f CLAUDE.md` and `readlink -f .brain/CLAUDE.md` resolve to their sibling
`AGENTS.md`, and reading through either path at a level shows identical content.

### 6. Verify

- [ ] Both levels were inspected before editing
- [ ] Each `AGENTS.md` is current against its template, with user content preserved
- [ ] `readlink -f` resolves correctly at both levels
- [ ] Public `AGENTS.md` scanned: only `.brain/AGENTS.md` appears, and a missing Brain is non-fatal
- [ ] No workspace-root files were touched

## Templates

- `templates/brain-AGENTS.md` — brain-level, private
- `templates/project-AGENTS.md` — repo-level, public
