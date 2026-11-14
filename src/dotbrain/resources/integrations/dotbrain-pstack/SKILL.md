---
name: dotbrain-pstack
description: >-
  Use the project's selected pstack workflow to implement, fix, refactor, verify,
  review, or resume engineering work. Applies in projects that explicitly enable
  the Dotbrain pstack integration; core context and tracker operations remain
  available independently.
---

# Dotbrain pstack

Run the selected engineering workflow using external pstack capabilities, the
private Brain, and the native Beads work graph. This mode owns the workflow;
Dotbrain's five core skills supply workspace and record operations. Selection
grants no additional authority to change scope, acceptance, publish, message
others, merge, deploy, or release. Reuse authority already granted by the user
and repository; do not ask for it again.

Apply the role in your assignment. The coordinator selects, claims, delegates,
accepts, and closes work. An implementation worker implements only its assigned
scope and returns the candidate, actual checks, and findings; it does not select
new tasks, take the coordinator's claim, or run this orchestration recursively.
A verifier inspects the assigned candidate read-only and returns its evidence and
verdict. Record-writing and further delegation require the assignment's authority.

## Establish the workspace

1. Read the checkout's `.brain/project.yaml` and ignored `.dotbrain-pstack.json`.
   Confirm opt-in, the selected source, and this runtime's delivered mode. Use
   `dotbrain doctor --json` from the checkout to check current dependency,
   backend, wiring, and delivery health. Resolve findings affecting this project
   and runtime before execution; unrelated machine findings remain reported
   gaps. A startup pointer alone is not requalification. Use `wire-brain` for
   setup/repair; do not edit generated metadata, caches, or runtime links.
2. Load the core `brain-convention`, `maintain-brain`, and `work-graph` operations
   as needed. If the matching core capabilities are unavailable, repair setup
   rather than reconstructing retired workflows. Run `bd prime` for the
   installed command protocol and inspect the actual store. Record native
   runtime/Beads versions when establishing an unattended run or qualification.
3. Read repository `AGENTS.md` and `RULES.md`, applicable domain vocabulary,
   relevant decisions, and the active design before choosing an approach.
   Search private `docs/` for existing explanations before re-investigating.
   Retrieve optional historical findings only when relevant; no notebook or
   retrospective ceremony is required. A read-only request remains read-only:
   return findings to its authorized writer without taking implementation or
   record-writing authority.

Done means the correct shared Brain/store, current selection, applicable
requirements, task scope, and authority are known. Unsupported or missing
dependencies hold affected execution; core operations remain independently usable.

## Select and shape work

Read [Pstack routing and adaptations](references/pstack.md) before invoking an
upstream capability. It names the compatible leaves and replaces conflicting
entrypoints explicitly. Use the source recorded in local metadata, never an
arbitrary global copy or the upstream top-level mode in parallel with this one.

- For a bounded task with a settled shape, inspect its affected callers and use
  the smallest complete change. Read pstack's `principle-prove-it-works` before
  verification and the relevant principle leaf when its guidance changes a
  decision. Use `tdd` for a requested regression or an obvious cheap bug test.
- For unfamiliar behavior or an unsettled boundary, use `how`/`why`, then
  `architect`/`arena` when competing shapes need exploration. Accepted designs
  constrain implementation; do not restart settled product decisions.
- Investigations return verified findings, unresolved hypotheses, and evidence.
  The authorized writer captures them through `maintain-brain`. Keep accepted
  vocabulary in `CONTEXT.md`, consequential accepted decisions in `adr/`, active
  initiative intent/uncertainty in `designs/`, and maintained findings in `docs/`.
  Recording an observation never adopts a decision or changes acceptance.
- Use `work-graph` to represent durable tasks, acceptance, dependencies, and
  pending improvements in Beads. Link a design through `spec_id`. Temporary
  procedural todos may describe steps within one task; reconcile unfinished
  work into Beads before handoff. Do not create a second task database.

Select from scoped `bd ready` results after checking authorization, dependencies,
operator gates, and capacity. Read [Ownership and recovery](references/continuity.md)
before claiming or delegating. The coordinator claims each eligible task under
its own actor. Conflicting claims hold that task; unrelated eligible work may
continue. Preserve existing criteria, prior attempts, and consumed limits.

For unattended work, record scope, completion/checks, permitted delivery, and
the user's stop conditions in Beads. Otherwise bound the next assignment and
choose a proportional stop condition. An explicit user override of limits is
recorded with its history; it does not change criteria or execution authority.

## Delegate and verify

Choose independent workstreams by file/resource ownership and shared mutable
state. Use pstack's exploration/coverage methods where they help; a settled small
change needs no duplicate design ceremony. Keep one active writer per assigned
resource. Workers do not own the coordinator's Beads claims.

Use local isolated Git worktrees for writing delegates. Attach each through
`dotbrain wire` so it shares the Brain/store and receives its project mode.
Pass the delivered mode's absolute path, task ID, coordinator actor, assignment
identity, source/context pointers, owned files, candidate branch, checks,
limits, and authority. Tell each worker it is not alone and must preserve others'
changes. Give the worker a bounded assignment, including whether it may delegate.
Record the actual ID returned by native Agent/spawn tools; no packaged Dotbrain
agent role is required. On Windows, automate PowerShell with `pwsh -NoProfile`.
Configured pstack model roles use available native models and
documented fallbacks; report lost diversity, never claim it or change providers
silently.

The coordinator records returned worker identities, candidate revisions, checks,
and unresolved results on the task. Check the actual Git objects and diff. A
worker's success narrative is not acceptance. Arrange an independent verifier for
behavior changes, supplying the exact candidate, requirements, checks, and
private-context boundary. Verify on the affected surface; retain a failed or
inconclusive check as such. Repair within the current grant and limits, then
refresh evidence for changed candidates. Keep work open while required evidence
or ownership is unresolved; never weaken a check to close it.

## Capture and deliver

Before accepting work, use `maintain-brain` to capture verified constraints,
resolved unknowns, decisions actually authorized, and remaining hypotheses with
their evidence. Reconcile concurrent private edits before saving. Use
`repo-rules` for adopted public requirements and routing; implementation of
enforcement remains engineering work. Derive public wording independently:
private identifiers, paths, source excerpts, and sentinels stay private.

At initiative handoff, update the active design's verification and pending
outcomes through `maintain-brain`. Terminal lifecycle needs the actual shipment,
abandonment, or supersession evidence and applicable authority. Closing tasks or
opening a PR does not by itself mark a design shipped.

Integrate the verified candidate and recheck its interactions. Close prerequisite
tasks only when their own acceptance passes, then inspect readiness before
claiming dependent integration work. Record the exact revision, environment,
actual checks, verdict, gaps, and artifact locations in Beads before unforced
closure. Task acceptance, PR review/merge, and release are separate outcomes.
Deliver only what the current user/repository grant permits, with appropriate
review and checks. A selected mode never authorizes an external write by itself.

At interruption, pickup, worker replacement, or a late result, follow the
continuity reference. Recover from Beads and the owning Brain records; a prior
transcript may supplement them but cannot be the only resume mechanism.
