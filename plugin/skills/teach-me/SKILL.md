---
name: teach-me
description: "Teaches the user a code project over multiple sessions from its private Brain: explains concepts in conversation, walks a learning path through a topic, and captures agreed lessons and references into `.brain/learning/`. Use when the user says 'teach me', 'help me learn/understand X', 'walk me through', 'quiz me', 'continue my learning path', or 'write a lesson on'."
---

# Teach Me

Invoking this skill is a request to be taught, not a request for files. Teach in the conversation
first. Write a lesson only when the user agrees to capture what was learned: a lesson drafted before
the learning records what the agent knows, not what the user does.

## Stop before you start

- **The question needs one quick answer mid-task.** Answer it and carry on.
- **The repository has no `.brain/`.** The workspace lives in the project Brain, so say the repository
  needs wiring first (`wire-brain`) and stop.
- **The user wants code changed.** Teaching never authorizes implementing, pushing, or deploying.

## The workspace

All learning state lives in the project Brain at `.brain/learning/`. It is private and is never
copied into the public repository:

- `AGENTS.md`: the workspace's own rules, including whether a learning site renders its pages and
  where that site's publishing guide is.
- `MISSION.md`: why the user is learning this project, with one section per topic
  ([format](./references/mission-format.md)).
- `learning-records/`: what the user has demonstrated, each tagged with its topic
  ([format](./references/learning-record-format.md)).
- `RESOURCES.md`: trusted sources, grouped by topic plus a Shared group
  ([format](./references/resources-format.md)).
- `GLOSSARY.md`: the project's canonical terms ([format](./references/glossary-format.md)). Every
  lesson follows it.
- `NOTES.md`: the user's stated teaching preferences.
- `lessons/` and `reference/`: captured pages ([format](./references/lesson-format.md)).

The hierarchy is **project → topic → lesson**:

- The **project** is the repository whose Brain this is. One Brain has one learning workspace.
- A **topic** is a named area of learning: one `### ` heading under `## Topics` in `MISSION.md`.
- A **lesson** teaches one practical skill within one topic. Its `##` headings are its sections.
- A **reference** is a compact lookup page that supports one topic's lessons.

If `.brain/learning/` does not exist yet, create it once the user confirms the first topic. Write
`MISSION.md`, `RESOURCES.md`, and `NOTES.md` first. Create `GLOSSARY.md` and `learning-records/` when
their first entry exists.

## Learning paths

A **learning path** is an ordered list of lesson-sized steps through one topic, tied to that topic's
section of the mission. A path finished in one session exists only in the conversation. A path that
spans sessions is a bead titled `learn: <topic> path`, labelled `learning`, and kept deferred so it
never reaches the ready frontier. The steps go in its description, and each step's progress and what
it still owes are appended to its notes, never rewritten. The bead tracks where
the path is. Only learning records hold what the user knows.

Other sessions park concepts for later learning as notes on a deferred `learn: <topic> backlog`
bead, whose topic they inferred without reading this workspace. Those topics are guesses, and step 1
reconciles them. When the project has no execution engine, there are no learning beads: paths live
in the conversation and nothing is parked.

## Workflow

### 1. Infer the context

Work out what the user is asking about, which code or system it concerns, and which topic it belongs
to. Read the repository `AGENTS.md`, `.brain/AGENTS.md`, `.brain/learning/AGENTS.md`, `MISSION.md`,
`NOTES.md`, and that topic's learning records. When the user is resuming a path ("continue step 3"),
also read its `learn:` bead.

List the open learning beads (`bd list --label learning`). When backlog beads exist, reconcile them
before teaching, and offer their concepts as candidates for this session:

- Assign each backlog to an existing topic, or propose a new topic following step 2. Merge backlogs
  that turn out to share a topic, and retitle a backlog whose inferred topic was renamed.
- With the user, group the parked concepts into lesson-sized steps: add them to the topic's learning
  path bead, or turn the backlog into a learning path bead when the topic has none.
- Record each concept's outcome by appending a line to the backlog's notes ("<concept>: folded into
  step 3", "taught", "dropped"), and close a backlog once none of its concepts is left unsorted.

Completion: a topic is named, either existing or proposed; its learning records have been read; any
path being resumed has been read; and every open backlog is either reconciled or left for a later
session by the user's choice.

### 2. Confirm the intention

When the user is resuming a path, skip this step and continue at the next step the bead shows as
owed. When they already said exactly what to capture ("write a lesson on X for Azure operations"),
skip to step 5.

Otherwise, state the inferred topic, then ask what the user wants: understand this question now,
walk a learning path through the topic, or capture a lesson.

- Propose a new topic by its name and why it stands apart from the existing ones.
- If the mission, or this topic's section of it, is missing or vague and the context does not show
  what the user intends, interview them first: why they want this, and what they want to be able to
  do. Then draft the why and what success looks like, following
  [mission-format.md](./references/mission-format.md), and write it once the user accepts it.

Completion: the user has confirmed the topic, its mission section, and what they want from this
session.

### 3. Teach in the conversation

Read [pedagogy.md](./references/pedagogy.md) before the session's first explanation. Answer the
user's actual question in small steps, grounded in `RESOURCES.md` and the code, then ask retrieval
questions.

For a broad goal, propose a learning path and walk it with the user, adjusting it as they learn. When
the user agrees to a path that will span sessions, create its learning path bead with
`bd create "learn: <topic> path" --labels learning`, then `bd defer` it.

Completion: the user has answered a retrieval question on each point taught; every misconception
has been corrected; and, when walking a path, the user has agreed to the path.

### 4. Record what was demonstrated

Write a learning record for each non-obvious understanding the user showed and each misconception
you corrected. When walking a path, write the step's records before you mark the step done in its
bead's notes. A bead note is progress, not a record: the next session reads the records to set the
level.

If the user does not want a lesson, the run ends here.

Completion: every point from step 3 that the next session needs has a learning record, and any path
bead shows the step's status and what it still owes.

### 5. Propose the shape

Give the title, the topic, and the lesson's position among that topic's lessons ("Azure operations,
3 of 3"). Then give the `##` sections, the retrieval questions, the primary source, and whether a new
reference is needed or an existing one should grow.

Completion: the user has approved the shape.

### 6. Capture

Write the lesson and its reference following [lesson-format.md](./references/lesson-format.md). If
`.brain/learning/AGENTS.md` names a learning site, also follow that site's publishing guide and run
its check. Committing the Brain, and anything outward, waits for the user's go-ahead.

The lesson is captured when it names a mission topic, links to its reference and back,
`GLOSSARY.md` and `RESOURCES.md` cover every new term and source it uses, and any named site's check
passes.

## Revising existing material

To fix, extend, or update a lesson or reference (an error, changed code, a lesson folding into a
reference), first propose the change and its reason. Then edit the page in place following
[lesson-format.md](./references/lesson-format.md). Keep the file name: it is the page's identity,
and its number sets the lesson's place in its topic.

## Code grounding

Ground explanations in the repository's current checkout, read at the time of teaching. When a
lesson's claim depends on code, record the commit it was checked against in its Code basis. Link code
by permalink at that commit on the public remote, so the claim stays checkable after the code moves.
When the user asks to refresh a lesson, compare its claims against the current code, revise what
changed, and move its Code basis forward.

Learning material stays in the Brain. When something learned would help public readers, write a new
page for them in the public docs; do not copy the lesson.

## Rationalizations to Reject

| Shortcut | Why it is wrong |
|---|---|
| Draft the next lesson now to save a session | It records what the agent knows; the lesson must capture what the user demonstrated. |
| Explain from memory and cite later | Parametric knowledge is a lead; `RESOURCES.md` and the code are the sources. |
| Skip the learning record because a lesson was written | The lesson is for reading; the record steers the next session's level. |
| Note the step's outcome on the learning path bead instead of a record | The bead tracks where the path is; only records carry what the user knows. |
| Rename or renumber a lesson file to tidy the list | Its file name is its identity and its number is its place in the topic. |
