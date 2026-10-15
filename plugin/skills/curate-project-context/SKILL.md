---
name: curate-project-context
description: Curates a project's public and private agent context. Use when checking context health, reorganizing accumulated guidance, repairing AGENTS.md or CLAUDE.md drift, finding stale, duplicated, misplaced or unreachable knowledge, or checking the public/private boundary.
---

# Curate Project Context

Keep the context system of a project coherent as it grows. Inspect public repository context,
private Brain knowledge, and the pointers between them; identify maintainability problems; then
apply only the repairs the user authorizes.

This skill has two modes:

- **Check** is the default. Diagnose and report without changing files.
- **Fix** applies findings the user explicitly asks to repair. An explicit request to organize,
  maintain, or fix the context authorizes repairs within the named project, but not lifecycle work
  owned by another skill.

## Scope limits

Fix mode writes files, so these bound what it may change:

- **Relocate settled facts, never adjudicate one.** A contested term or an unmade decision goes to
  `grill-decisions`; moving a fact is in scope, deciding it is not.
- **Report wiring, do not repair it.** `dotbrain doctor` supplies the mechanical baseline and
  `wire-brain` fixes it; use their evidence and route the repair.
- **Never touch another document's lifecycle.** Design closure and residue promotion are
  `close-design`'s; Beads state is `manage-work-graph`'s.
- **Credentials belong in the configured secret store**, never in public or private context files.

`write-agent-docs` supplies the writing discipline for pointers, hierarchy, completion criteria, and
pruning. Apply it when revising prose.

## Authority map

Classify each piece of project knowledge by its durable authority:

| Information | Authority |
|---|---|
| Task-specific retrieval and essential constraints | Public `AGENTS.md` |
| Established repository rules for making or reviewing changes | Tracked root `RULES.md`, routed from public `AGENTS.md` |
| Shared Brain operations and private retrieval | `.brain/DOTBRAIN.md` |
| Private retrospective findings and evidence | `.brain/RETRO.md`, maintained by `retro` |
| Domain vocabulary | `.brain/CONTEXT.md` |
| Durable decisions and rationale | `.brain/adr/` |
| Initiative-specific working design | `.brain/designs/` |
| Execution status and work notes | Beads |
| Supporting explanation | A public or private referenced document chosen by sensitivity |

Public and separately scoped `AGENTS.md` files retain their roles; each sibling `CLAUDE.md`
is a relative symlink to `AGENTS.md`. The two root private Brain entry files are retired,
not an optional instruction layer. Public context remains useful without a Brain.
Public rationale stands on its own; private paths, record identifiers, and tracker state stay private.

## Check

### 1. Inventory the context surface

Read the nearest project instructions, then enumerate relevant public and private `AGENTS.md` and
`CLAUDE.md` files, treating root private entry files only as legacy migration residue.
If the project is wired, inspect `.brain/DOTBRAIN.md`,
`.brain/CONTEXT.md`, `.brain/project.yaml`, ADR and design indexes or frontmatter, and documents
reached by context pointers. Load full ADRs, designs, or supporting docs only when a finding requires
their content.

Run `dotbrain doctor` when available to establish the mechanical baseline. Report its wiring
findings separately from content-maintainability findings.

Completion: every context surface and pointer relevant to the project has a known location,
visibility, authority, and mechanical state.

### 2. Test topology and boundaries

Check that pointers resolve and required material is reachable under the condition that needs it.
For public and separately scoped entry files, check that `CLAUDE.md` symlinks resolve to the
canonical sibling `AGENTS.md`; impose no canonical relationship on retired root private entries.
Verify that public context still
works without a Brain, routes making and reviewing changes to root `RULES.md`, and contains
no private Brain material.

Completion: every broken link, weak pointer, invalid canonical relationship, and public/private
boundary violation is identified with its exact path and evidence.

### 3. Test authority and maintainability

Apply the authority map and `write-agent-docs` principles. Look for:

- the same meaning maintained by more than one authority;
- conflicting instructions or vocabulary across levels;
- stale guidance contradicted by the repository, configuration, or current Brain canon;
- easy environment lookups cached in prose without a useful convention, rationale, or hazard;
- knowledge stored in the wrong authority, including decisions or execution state in `AGENTS.md`;
- unreachable or orphaned documents, and pointers whose trigger does not name the branch that needs
  them;
- sprawling files whose branch-specific detail should be disclosed;
- private information in public context, or public operating knowledge hidden unnecessarily in the
  Brain.

Completion: each suspected problem is either supported by current evidence or discarded.

### 4. Report

Present findings in priority order:

| Finding | Evidence | Correct authority | Proposed repair | Owner |
|---|---|---|---|---|

Distinguish repairs this skill can apply from work routed to `wire-brain`, `grill-decisions`,
`close-design`, or `manage-work-graph`. A clean check says so and lists the surfaces examined.

Completion: every finding has an exact target and no proposed repair silently changes project
meaning or another document's lifecycle.

## Fix

Apply only the findings authorized by the user. Preserve meaning and useful history while moving a
fact to its authority, removing an exact duplicate, sharpening a pointer, pruning stale guidance,
or repairing an `AGENTS.md`/`CLAUDE.md` relationship. Back up a meaningful regular `CLAUDE.md`
before replacing it with a symlink.

After a move, update every pointer that should still reach the material. Keep public edits safe for
publication and scan the final public files for private Brain paths and identifiers. Re-run the
check against every changed surface and report any findings routed to other skills.

Completion: all authorized repairs are verified, unapproved findings remain untouched, and each
piece of moved knowledge has one reachable authority.

## Explicit legacy entry migration

Run only for a selected repository-backed project under an explicit migration request.
Generic `wire` and `refresh` preserve user-owned entry files, notebooks, repository rules,
and instructions. Brain-only projects and unavailable checkouts remain outside this migration.

1. Inventory both root private entry files (`.brain/AGENTS.md` and `.brain/CLAUDE.md`),
   including regular-file content, symlink targets, and any distinct content behind each link.
   Retain a private snapshot and a source-to-destination inventory before moving anything.
   Completion: every useful passage and every link has a recorded disposition.
2. Relocate vocabulary to `CONTEXT.md`, decisions to ADRs, and supporting material to existing
   appropriate references. Derive public rules into tracked root `RULES.md` with standalone
   rationale; route making/reviewing changes there from public `AGENTS.md`. Shared operations
   belong in the packaged convention. Preserve sensitive evidence privately. Established rules
   do not become retrospective findings without evidence. Do not create a catch-all private
   policy file. An unresolved private policy destination stops deletion of that entry.
   Completion: compare the retained source with every destination; all useful content is reachable.
3. Remove only the inventoried legacy entries after their destinations are verified. Unlink a
   symlink itself; never delete or rewrite its target. Preserve unrelated instructions, scoped
   entry files, notebooks, and foreign links. Remove obsolete Dotbrain-owned pointer blocks only.
   Completion: repeated refresh leaves retired files absent, preserved material unchanged, and
   public routing usable without a Brain. Report retained snapshots, destinations, and any gaps.
