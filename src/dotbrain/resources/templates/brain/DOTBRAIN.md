# DOTBRAIN.md

Shared Brainspace contract, owned by dotbrain and synced by `dotbrain refresh`.
Project knowledge belongs in the records below; this file is a packaged resource.

## Workspace and ownership

The code repository holds public source and repository requirements. The private
dotbrain home holds Brainspaces, selected skill and custom-agent sources, and
private file history. Each project Brainspace has a `.brain/` knowledge directory
and, when enabled, a `.beads/` work store. A checkout's gitignored `.brain` and
`.beads` links identify that shared project state. Linked Git worktrees share
these records while receiving checkout-local runtime resources.

Use `wire-brain` and the CLI for provisioning, attachment, repair, diagnostics,
resource reconciliation, and detachment. `project.yaml` declares runtime,
tracker, and selected custom resources. The CLI preserves user declarations and
sources; generated resources have their own ownership and collision rules.
Inspect reported collisions before changing them. Removing a checkout's wiring
does not delete the Brainspace or its work history.

## Records and provenance

| Record | Meaning |
| --- | --- |
| `CONTEXT.md` | Settled project vocabulary and domain model |
| `adr/` | Consequential accepted decisions and their rationale |
| `designs/` | Initiative intent, constraints, criteria, uncertainty, and lifecycle |
| `docs/` | Maintained findings, references, and explanations |
| `scratch/` | Run output: trails, plans, briefs, reports, evidence, measurements, prototypes; never committed |
| Beads | Tasks, dependencies, ownership, criteria, work state, and execution evidence |
| Repository `RULES.md` | Adopted public repository requirements |

`maintain-brain` provides context record operations. `work-graph` provides native
Beads graph operations. `repo-rules` initializes and reconciles repository
requirements when requested. These capabilities do not select an engineering
workflow; the selected workflow owns execution procedures.

These destinations apply when information needs durable preservation. Session
reasoning, temporary checklists, and disposable experiments may remain temporary;
files a workflow writes for one run go in `scratch/`. Preserve Brain understanding when
later work needs information that existing sources do not adequately retain.
Use Beads for work needing durable continuation or coordination, and keep existing
tracked work current. Honor explicit capture requests. A task may finish without
creating either record. Resume tracked work from Beads and relevant project sources.

Records distinguish observations, inferences, hypotheses, proposals, and accepted
decisions. A recorded discovery does not adopt a consequential decision. Keep
source and applicability beside a claim, and distinguish verified outcomes from
pending checks. Design lifecycle describes the initiative's document state;
Beads remains the authority for durable execution state. Terminal lifecycle
updates require evidence for the claimed outcome.

Before using a decision as a constraint, check its status, scope, and linked
amendments or replacement. Proposals and retired decisions provide context.
Code establishes current behavior; applicable adopted decisions establish intended
constraints. Surface material conflicts without assuming either source silently
revokes the other. Check the relevant decision, not the whole archive.

## Run output in scratch

Write each run's files in `.brain/scratch/<yyyy-mm-dd>-<slug>/`, with the slug naming
its task or tracked item. Create a new folder for every run, adding `-2`, `-3`, and so
on when the name is taken. Use `trail.tsv`, `plan.md`, `briefs/`, `reports/`,
`evidence/`, `measurements/`, and `prototype/`, adding another name only when none
fits. Home sync never commits `scratch/`, so it is neither backed up nor shared
between machines, and any run folder may be deleted.

Durable understanding leaves a run only by updating `CONTEXT.md`, an ADR, a design,
or a `docs/` record; otherwise nothing is kept. No record, pull request, or tracked
item cites a scratch path. Private evidence that must outlive the run goes into the
tracker or the promoted record; a pull request or the repository holds only public
material. Move reusable tools, models, and baselines to the repository or a skill.
Read scratch only through a path the current run or a brief names; Brain maintenance
and audits skip it.

## Safe maintenance and privacy

Reconcile the latest contents before saving concurrent edits. Within authorized
maintenance, remove obsolete or redundant records that no longer support current
understanding or unfinished work, retaining independently useful rationale and
evidence where needed and repairing pointers. Version history can provide recovery
without keeping obsolete files in the Brain. Preserve unrelated user content,
active requirements, work records, claims, dependencies, and remaining limits.
Reading a record does not itself require repairing it. Retiring a workflow does
not accept results, close work, or reset consumed limits.

Private Brain content and provenance stay private. Derive public guidance for its
audience without exposing private identifiers, paths, or source excerpts. Public
repository instructions remain useful without access to a Brainspace.

Home sync versions private files; Beads has its own backend persistence and backup
requirements. Neither mechanism replaces the other. Use the owning mechanism for
backup and recovery, reconciling newer work before restoring older state.
