# Learning beads

How to park a concept for later learning when the operator asks ("park this for learning", "I want
a lesson on this later"). Parking only files the concept; teaching it later belongs to `teach-me`.

## The shape

Each project has one **learning epic**, titled `Learning`, typed `epic`, labelled `learning`,
and kept deferred. It groups learning separately from implementation work; parentage alone does
not keep an item off the ready frontier.

Its children are labelled `learning` and their titles start `learn:`. Each covers one topic, so
the number of learning beads grows with topics, not with questions.

- **Learning path bead**, `learn: <topic> path`: an ordered learning path that spans sessions. `teach-me`
  creates and advances it.
- **Learning backlog bead**, `learn: <topic> backlog`: concepts parked for a topic, waiting to become lessons.

Reuse the project's learning epic. If absent, create it with
`bd create "Learning" --type epic --priority 4 --labels learning`, then `bd defer <epic-id>`.
Attach existing learning path beads and learning backlog beads with
`bd update <id> --parent <epic-id>`; keep each child deferred too. The epic is a persistent
container, not an initiative with a design or a completion gate.

A parked concept is one comment on a learning backlog bead, never a bead of its own. Each comment holds:

- the concept, named so a lesson could be built around it
- the question that raised it, and how it was answered in the session
- where it came up: the file or symbol, the commit, and the work underway

Every learning bead stays deferred, so none reaches the ready frontier. Comments are append-only:
record a correction or disposition in a new comment referencing the original comment id; never
edit or delete the original. Learning backlog Notes stay minimal. Learning path progress stays in
Notes and is appended with `--append-notes`, never rewritten.

## Parking a concept

1. List the open learning beads: `bd list --label learning`. Do not read `.brain/learning/`,
   `MISSION.md`, or its topics; matching against the open beads is enough.
2. Ensure the learning epic exists using the commands above. If an open learning backlog bead
   already covers the concept's topic, attach it to that epic, keep it deferred, and add a comment:
   `bd comments add <id> "<concept note>"`.
3. Otherwise, infer a topic name from the concept, create a learning backlog bead, defer it,
   then add the concept comment:

   ```bash
   bd create "learn: <topic> backlog" --type task --priority 4 --labels learning --parent <epic-id> \
     --description "Concepts parked for learning, reconciled by teach-me. Read the comments."
   bd defer <id>
   bd comments add <id> "<concept note>"
   ```

   An inferred topic that does not match the workspace's topics is expected. `teach-me` assigns it
   a topic, or proposes a new one, the next time it runs.
4. Confirm in one line, naming the bead, and return to the work underway. Do not load `teach-me`.

Learning beads are never feature work: do not claim one from the ready frontier, attach one to an
implementation epic, or close one while parking. `teach-me` owns their lifecycle after parking.
