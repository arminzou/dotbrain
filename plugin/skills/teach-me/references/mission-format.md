# MISSION.md Format

`MISSION.md` lives at `.brain/learning/MISSION.md`. It captures the _reason_ the user is learning this project, with one section per topic. Every teaching decision (what to teach next, which resources to surface, which exercises to design) should trace back to this document.

## Template

```md
# Mission: {Project}

## Why
{1-3 sentences. The concrete real-world goal the user is chasing. What changes in their life or work when they have this skill? Avoid abstract framings like "to understand X"; push for the underlying outcome.}

## Topics

### {Topic}

**Why:** {Why this topic, in the user's words.}

**Success looks like:**
- {A specific, observable thing the user will be able to do}
- {…}

## Constraints
- {Time, budget, prior commitments, learning preferences, anything that bounds the approach}

## Out of scope
- {Adjacent topics the user explicitly does not want to chase right now, protecting the zone of proximal development}
```

## Rules

- **One mission per project, one section per topic.** A new topic adds a section here; it never gets its own mission file. Two unrelated code projects are two projects.
- **Topic headings are identifiers.** Every lesson's and reference's `topic` field must match a `### ` heading under `## Topics` exactly, and a learning site may read those headings, in order, to group its pages. Keep `## Topics` and its `### ` headings in that shape; add only topic sections under it. Renaming a topic means updating the `topic` field of every page that names it.
- **Concrete over abstract.** "Run a half marathon by October" beats "get fitter." "Ship a Rust CLI to my team" beats "learn Rust."
- **Interview until the intention is clear, then draft.** When the mission or a topic's section is missing or vague, first judge whether the context shows why the user wants this. If it does not, interview them: ask why, what they want to be able to do, and what changes when they can, one question at a time. Once the intention is clear, draft the why and success criteria from the answers, the conversation, the codebase, and existing learning records, and recommend the draft for the user to accept or edit. A bad mission is worse than no mission, so write it only once the user accepts it.
- **Revise when reality shifts.** Missions change. When the user's goal moves, update this file: don't leave a stale mission steering future sessions.
- **Keep it short.** If `MISSION.md` runs past a screen, it has stopped being a compass and started being a plan.
