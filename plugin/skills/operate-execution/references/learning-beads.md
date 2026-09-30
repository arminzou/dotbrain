# Learning beads

How to park a concept for later learning when the operator asks ("park this for learning", "I want
a lesson on this later"). Parking only files the concept; teaching it later belongs to `teach-me`.

## The shape

A learning bead is labelled `learning` and its title starts `learn:`. Its scope is one topic, so the
number of learning beads grows with topics, not with questions.

- **Path bead**, `learn: <topic> path`: an ordered learning path that spans sessions. `teach-me`
  creates and advances it.
- **Backlog bead**, `learn: <topic> backlog`: concepts parked for a topic, waiting to become lessons.

A parked concept is a note on a learning bead, never a bead of its own. The note holds:

- the concept, named so a lesson could be built around it
- the question that raised it, and how it was answered in the session
- where it came up: the file or symbol, the commit, and the work underway

Every learning bead stays deferred, so none reaches the ready frontier. Notes are only ever appended
(`--append-notes`), never rewritten, because a path bead's notes also carry its step progress.

## Parking a concept

1. List the open learning beads: `bd list --label learning`. Do not read `.brain/learning/`,
   `MISSION.md`, or its topics; matching against the open beads is enough.
2. If an open backlog bead already covers the concept's topic, append the concept to its notes:
   `bd update <id> --append-notes "<concept note>"`.
3. Otherwise, infer a topic name from the concept and create a backlog bead with the concept as its
   first note, then defer it:

   ```bash
   bd create "learn: <topic> backlog" --type task --priority 4 --labels learning \
     --description "Concepts parked for learning, reconciled by teach-me." --notes "<concept note>"
   bd defer <id>
   ```

   An inferred topic that does not match the workspace's topics is expected. `teach-me` assigns it
   a topic, or proposes a new one, the next time it runs.
4. Confirm in one line, naming the bead, and return to the work underway. Do not load `teach-me`.

Learning beads are never feature work: do not claim one from the ready frontier, give one a parent
epic, or close one. `teach-me` owns their lifecycle after parking.
