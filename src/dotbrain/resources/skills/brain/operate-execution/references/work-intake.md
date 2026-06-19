# Work intake: bead vs PRD

This reference governs **when** new work enters the graph as a direct bead vs when an agent
should suggest a PRD + epic workflow. `operate-execution` reads this to make the call.

## Create a bead directly

Work can enter as a direct bead (without PRD) when ALL of the following are true:

- **Single unit** — the work is one thing, not a multi-step initiative
- **Well-scoped** — you (or the user) can describe what done looks like in a sentence or two
- **No architectural ambiguity** — the approach is obvious or already decided
- **No cross-cutting impact** — the change doesn't affect multiple systems, teams, or surfaces

Typical examples: a bug fix, a one-shot chore (rename, dep update), a simple feature with
clear acceptance criteria, a discovered follow-up task.

## Suggest a PRD + epic

Suggest the `to-prd` → `to-issues` workflow when ANY of the following is true:

- **Multi-step** — the work decomposes into 3+ distinct tasks
- **Scope ambiguity** — the boundaries aren't clear yet
- **Requires architectural decisions** — trade-offs need discussion
- **Cross-cutting impact** — touches multiple modules, APIs, or surfaces
- **Needs user-story clarity** — it's not obvious who benefits and how

The agent should raise the suggestion conversationally: "This looks like it could use a
PRD — want me to run `to-prd` and formalize it?" Do not force the workflow; offer it.

## Exceptions

- Bugs found mid-implementation: always create a bead directly (`--type bug`). A bug is not a
  feature and should not enter the PRD pipeline.
- User explicitly asks for a specific path: respect their preference, don't re-offer.
