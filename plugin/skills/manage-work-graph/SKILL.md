---
name: manage-work-graph
description: Maintains the project's private work graph — files, shapes, links, claims, records outcomes for, and closes work items. Use for any interaction with the project issue tracker — filing work items, inspecting the ready frontier, claiming, updating status, applying closure. Hands implementation of an item or finite batch to run-execution. NOT for decomposing a design doc into an epic (to-issues), formalizing an initiative (to-design), closing one out (close-design), or triaging public issues (triage-public).
---

# Manage Work Graph

Maintain the Brainspace's private **work graph**: a typed, prioritized dependency graph of work
items that says what work exists and what it depends on. The engine is declared in `project.yaml`
(`execution-engine:`) and is beads in practice: this skill and the design-lifecycle skills use
`bd` directly. This file owns the model and graph maintenance;
[references/beads.md](references/beads.md) owns how to express work in beads' native fields.

This skill owns the **work graph**: work items and their dependency edges. The **ready frontier**
(open items with no open blockers) is the set eligible to start; blocking edges are the
serialization. The **execution graph** (how an agent team carries out a fixed set of items) and each
item's **execution record** belong to `run-execution`
([its reference](../run-execution/references/execution-record.md)).

Boundaries:

- **Private work graph** — work items in the engine's store; this skill owns it and it is the
  source of truth. Never mirror work state into markdown docs, ROADMAPs, TodoWrite/task lists, or
  a public issue tracker.
- **Public issue tracker** — handled by `triage-public`; existing public collaboration may be
  promoted inward with a provenance link, but private work is never published outward for tracking.
  See [references/public-provenance.md](references/public-provenance.md) when work crosses that
  boundary.
- **Knowledge layer** — `.brain/CONTEXT.md`, `.brain/adr/`, `.brain/AGENTS.md`, `.brain/DOTBRAIN.md`; owned by other skills.

## What this skill owns

- work intake: a direct work item or the design-doc path ([references/work-intake.md](references/work-intake.md))
- shape epics, tasks, dependencies, and acceptance criteria
- read the ready frontier within an authorized scope and recommend the smallest useful continuation
- ownership: claims and assignees on work items
- record item outcomes and absorb discoveries back into the graph when work reveals new reality
- apply closure rules: native closure when acceptance evidence passes and item-level human gates
  are resolved
- preserve provenance when an existing public issue is promoted into private work
  ([references/public-provenance.md](references/public-provenance.md))
- record a code review's findings as a review bead
  ([references/review-beads.md](references/review-beads.md))
- park a concept for later learning on a learning bead
  ([references/learning-beads.md](references/learning-beads.md))

Implementing an item — dispatch, integration, checks, bounded repair, escalation, and recovery — is
`run-execution`'s. A plain request to do the work starts it.

## Stop before you start

- The work is a multi-item initiative, not a single item — it needs a design doc first. The call
  between a direct work item and that path is [references/work-intake.md](references/work-intake.md).
- An epic exists but has no child work items — it has not been decomposed yet; run `to-issues`.
- The item is human-gated — stop for sign-off before claiming it (see [Ownership and closure](#ownership-and-closure)).
- The item is a `learn:` bead (label `learning`) — it tracks the operator's learning, not work;
  `teach-me` resumes and updates it.

Branch selection and delivery follow [run-execution](../run-execution/SKILL.md).
Session invariants follow the dotbrain convention.

## Who writes the graph

Roles follow the agent team: the **lead** runs one execution and dispatches **workers**; the
**assignee** is the actor holding an item's claim.

- Without delegated workers, the session doing the work is the lead and may shape, claim, update,
  split, create, and close items as discoveries emerge.
- During an execution with delegated workers, the lead is the only agent that changes the work
  graph and edits the active design doc. A delegated worker writes only its own claim and, when
  assigned, evidence comments on its own item. It returns discovered work and design-relevant
  learning to the lead, who records them.

## Ownership and closure

Apply the convention's human gates and criteria ownership before claiming or closing.
Claim only work you will do yourself; a delegated worker performs its own startup under
its [role contract](../../agents/worker.md) (in Codex, `.codex/agents/dotbrain-worker.toml`).
Never claim an epic merely to anchor scope.
Pass your own `--actor <actor>` on every tracker write. The lead alone writes execution
metadata. A worker retains its claim through candidate return and every fix round;
returning a candidate changes neither assignee nor claim. Claimed work stays out of
`bd ready`; lease expiry does not release a claim or permit another actor to claim it.

Only the assignee can close. The lead closes accepted work under the worker's actor,
naming itself in the reason and preserving the assignee:
`bd close <id> --actor <worker-actor> --reason "<reason> (closed by <lead-actor>)" --json --quiet`.
Never use `bd close --force` or `bd reclaim` on a worker's item.
Move a claim only after the former worker is confirmed stopped:
`bd update <id> --assignee <new-actor> --force --actor <lead-actor>`.
Record `Claim moved: <from actor> -> <to actor>`; uncertain termination needs the human.
See run-execution's parallel reference for replacement workers and retained artifacts.

Native closure requires acceptance evidence and resolved item-level human gates.
Apply [run-execution's acceptance rules](../run-execution/SKILL.md#item-review-and-acceptance)
for implementation and [review-bead closing rules](references/review-beads.md#closing)
for reviews. Closure never merges the target branch or automatically invokes `close-design`.
Leave the design and epic active until the human asks for terminal closeout; a ready PR
awaits human approval and merge.

## Metadata write method

Write only changed keys with `bd update <id> --metadata '<json-object>' --actor <actor> --json --quiet`.
Beads merges one level deep: unnamed keys survive; named values are replaced whole.
Write each changed `dotbrain_attempts` or `dotbrain_artifacts` value complete, not just
the changed entry. `--set-metadata` stores an object as an escaped string; use it, if at
all, for `dotbrain_phase` alone. Query with `bd list --metadata-field <key>=<value>`;
add `--all` for closed items. Keep logs in evidence comments, never metadata.

Write comment files verbatim in a temporary location outside the project. Prefer the
runtime file-writing tool. Shell fallbacks are quoted heredocs in bash/zsh (including
Git Bash) or single-quoted here-strings in PowerShell 7 with UTF-8 without BOM.
Never use `printf` or `echo -e` for comment text: Windows path backslashes become
control characters. Append with `bd comments add <id> --file <file> --actor <actor> --json`.

## Operating loop

1. On a new session or after context recovery, run `bd prime` for the Beads protocol. dotbrain
   injects no Beads context; skip it only when the operator's own Beads hook already supplied it.
   Read `.brain/AGENTS.md` for private tracker conventions (absent or empty means defaults), and follow public repository instructions/root `RULES.md`; read [references/beads.md](references/beads.md) (engine mechanics and native-modeling
   rules), and [references/work-intake.md](references/work-intake.md) (bead vs. design doc), then
   project Brain context and relevant ADRs.
2. Inspect the graph with structured, non-interactive output: ready frontier, list, and item detail
   (commands in [references/beads.md](references/beads.md)).
3. Check for human-gated items among the ready set (engine reference covers the command). Recheck
   every iteration: the gated set changes as items close and new ones are created.
4. Select the next ready item, skipping learning beads (label `learning`), which are not work:
   - **Human-gated** — stop for sign-off before claiming.
   - **Autonomous** — proceed. Claim it here only when this session will work it as a team of
     one; when workers will be dispatched, `run-execution` claims under each worker's own actor.
5. If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md` before
   implementing. Beads carry execution facts; the design doc carries the design,
   rationale, and file-level scope — do not infer those from the compressed acceptance criteria
   alone.
6. Hand implementation to `run-execution` with the selected item or finite batch.
   Apply the ownership and closure rules above when its acceptance gate passes.
   For existing public issues, use [public provenance](references/public-provenance.md).
   `bd close` remains the private close signal.
7. Follow the closure boundary above; review records follow `review-gate`.
8. When implementation exposes hidden requirements or follow-up work: do the obvious in-scope work
   directly; create or update related items when new work becomes explicit; split or reshape the
   current item when it is no longer the right shape; adjust dependencies within approved scope.
   Follow the convention's criteria ownership rule. Put discoveries back into the graph, never into ad hoc todo files.
9. Return to step 2. Continue until the ready frontier is empty or hits a human-gated item
   whose decision you're not present to make.

## Handoff context

When work moves to another agent or session before it closes, record enough that the next
assignee can act without being spoon-fed: work-item ID, anchor epic (if any), intended scope,
required checks, review/landing expectations, and the bead's current state: done, next, and any
open question. A branch created for the work uses a short descriptive slug and never a work-item
ID: branch names reach the public repo, and the item's record already names its branch.

## Review beads

Once any code review's findings need to survive the session — the user asks for a review bead, or
it's the natural next step after a review pass, whatever skill or process ran it — see
[references/review-beads.md](references/review-beads.md). It covers the single-pass and multi-pass
shapes a review bead can take, one generalized recipe regardless of which review produced the
findings, and how to recognize an existing bead's shape before operating on it.

## Learning beads

When the operator asks to park a concept for later learning, see
[references/learning-beads.md](references/learning-beads.md). It covers the path and backlog bead
shapes, the concept comment, and how to file one without leaving the work underway.
