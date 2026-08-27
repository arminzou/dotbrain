---
name: curate-project-context
description: Curate and maintain a project's public and private agent context. Use when checking context health, reorganizing accumulated guidance, repairing AGENTS.md or CLAUDE.md drift, finding stale, duplicated, misplaced or unreachable knowledge, or checking the public/private boundary.
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

## Boundaries

- `/init` or the runtime's equivalent owns initial public project scaffolding.
- `dotbrain doctor` checks mechanical installation and wiring; `wire-brain` repairs Brainspace and
  workspace wiring. Use their evidence, but do not absorb their jobs.
- `write-agent-docs` supplies the writing discipline for pointers, hierarchy, completion criteria,
  and pruning. Apply it when revising prose.
- `grill-decisions` resolves contested vocabulary and durable decisions. This skill may relocate an
  already-settled fact but does not invent or adjudicate one.
- `close-design` owns design closure and residue promotion. `operate-execution` owns Beads state.
- Credentials belong in the configured secret store, never in public or private context files.

## Authority map

Classify each piece of project knowledge by its durable authority:

| Information | Authority |
|---|---|
| Public project purpose, commands, conventions, and hazards | Public `AGENTS.md` or a public document it points to |
| Private operating rules and tracker conventions | `.brain/AGENTS.md` |
| Domain vocabulary | `.brain/CONTEXT.md` |
| Durable decisions and rationale | `.brain/adr/` |
| Initiative-specific working design | `.brain/designs/` |
| Execution status and work notes | Beads |
| Supporting explanation | A public or private referenced document chosen by sensitivity |

The repo-root and private `AGENTS.md` files are canonical at their level. Each sibling `CLAUDE.md`
is a relative symlink to `AGENTS.md`. Public context may point to `.brain/AGENTS.md`, but must remain
useful when the Brain is absent and must not expose private Brain content. Public rationale stands
on its own; other Brain paths, ADR numbers, private-record identifiers, and tracker state stay in
the Brain.

## Check

### 1. Inventory the context surface

Read the nearest project instructions, then enumerate relevant public and private `AGENTS.md` and
`CLAUDE.md` files. If the project is wired, also inspect `.brain/DOTBRAIN.md`, `.brain/AGENTS.md`,
`.brain/CONTEXT.md`, `.brain/project.yaml`, ADR and design indexes or frontmatter, and documents
reached by context pointers. Load full ADRs, designs, or supporting docs only when a finding requires
their content.

Run `dotbrain doctor` when available to establish the mechanical baseline. Report its wiring
findings separately from content-maintainability findings.

Completion: every context surface and pointer relevant to the project has a known location,
visibility, authority, and mechanical state.

### 2. Test topology and boundaries

Check that pointers resolve, required material is reachable under the condition that needs it, and
`CLAUDE.md` symlinks resolve to the canonical sibling `AGENTS.md`. Verify that public context still
works without `.brain/` and contains no private Brain material beyond the permitted optional
pointer.

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
`close-design`, or `operate-execution`. A clean check says so and lists the surfaces examined.

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
