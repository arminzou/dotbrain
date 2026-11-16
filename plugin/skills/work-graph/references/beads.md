# Native Beads operations

Run `bd prime` for the installed protocol and use subcommand help for an unknown
or rejected option. Commands below illustrate the native interface. Supply the
applicable actor and operate against the intended store.

```sh
bd where
bd ready --json --quiet
bd show <id> --long --json --quiet
bd list --status open --json --quiet
bd create "Work outcome" --type task --acceptance "Observable completion" --actor <actor> --json --quiet
bd create "Initiative" --type epic --spec-id design:<slug> --actor <actor> --json --quiet
bd create "Child outcome" --parent <epic> --type task --actor <actor> --json --quiet
bd update <id> --claim --actor <actor> --json --quiet
bd dep add <blocked-item> <prerequisite> --actor <actor> --json --quiet
bd close <id> --reason "Accepted outcome and evidence" --actor <actor> --json --quiet
```

## Fields and relationships

| Native concept | Meaning |
| --- | --- |
| Type | The kind of work, such as task, bug, feature, chore, or epic. |
| Priority | Ordering among eligible work. It does not create a dependency. |
| Parent-child | Structural grouping. Parentage alone does not serialize execution. |
| Blocks | A prerequisite that withholds dependent work from readiness. |
| Related | A navigational relationship without a readiness gate. |
| Discovered-from | Provenance for new work uncovered during another task. |
| Assignee | The actor accountable under the selected workflow's claim model. |
| Acceptance criteria | The agreed outcomes defining completion. |
| Spec ID | The link to an initiative's owning design record. |
| Comments and artifacts | Append-only execution evidence and supporting material. |

`bd dep add A B` means A depends on B. Inspect the resulting edge direction.
Readiness is computed from state and prerequisites. A copied ready label or
another persistent checklist cannot replace that query.

## Ownership and failure

Use the native atomic claim operation to acquire an eligible assignment. For a
conditional ownership update, the installed protocol supports preconditions
such as `--if-assignee` and `--if-status`. A failed guard writes nothing and
requires inspecting current state. Apply the installed version's ownership
requirements when releasing, reassigning, or closing.

Establish that a previous writer has stopped or relinquished authority before
transferring its active responsibility. Retain candidates and evidence. The
chosen workflow owns the termination evidence, handoff procedure, and operator
decision when authority remains uncertain.

Use native closure protections. Force closure can bypass blockers or children,
so it is unsuitable for ordinary acceptance. A command's successful exit alone
does not establish a native-agent journey, a passing review, or a merge.

## Evidence and persistence

Link consequential evidence to the candidate revision and environment. Preserve
failed attempts, superseded conclusions, remaining limits, and unresolved gaps.
Update notes with the current resume state rather than replacing evidence
history. Discoveries with durable project meaning also belong in the Brain,
using `maintain-brain`.

Beads owns the execution database. Dotbrain home sync versions private files
through Git. Tracker backup or sharing uses the configured Beads backend and
its supported mechanisms. Confirm the applicable persistence operation rather
than assuming one backs up the other.
