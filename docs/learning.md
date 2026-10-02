# Learning Your Project

Dotbrain helps you learn the project you work on across sessions. The `teach-me` skill teaches
from your project's Brain and current code, checks your understanding, and keeps enough private
learning state for the next session to pick up where you left off.

Start in a [wired project](getting-started.md) with the dotbrain plugin installed. Ask your agent:

> Teach me how this project handles failed deliveries. I want to be able to diagnose one myself.

The agent confirms the topic and your goal, then teaches in conversation. A quick question during
implementation can stay a quick answer; it doesn't need a learning path or a saved lesson.

## Progress and Understanding Are Different

A learning path describes the steps toward your goal. A learning record captures evidence of
what you understand. Keeping those separate lets a future session recover both your position
and the right level of explanation.

| Artifact | What it holds | What the next session uses it for |
| --- | --- | --- |
| Learning path bead | Lesson-sized steps in Description; progress and next steps in Notes | Find where to resume |
| Learning record | Understanding you demonstrated, prior knowledge you stated, or a corrected misconception | Choose what to teach and check next |
| Learning backlog bead | One comment per concept parked for later | Offer questions to fold into the path |
| Captured lesson and reference | An approved explanation and supporting lookup page | Read or practice later |

Discussion alone does not establish understanding. The agent asks you to explain a concept or
perform an exercise, gives feedback, and writes a learning record when there is evidence worth
retaining. It writes that record before marking the learning path step complete.

## Walk a Learning Path

For a broad goal, ask for a path:

> Help me learn the retry mechanism over a few sessions. Start with one practical exercise.

The agent agrees the topic, goal, and path with you. A path that spans sessions becomes a
`learn: <topic> path` learning path bead. A short path finished in one session can stay in the
conversation.

The learning workspace belongs to the project. Topics organize its lessons; they are named in
`learning/MISSION.md` inside the Brain. The mission says why you are learning and what you want
to be able to do. Teaching preferences and trusted sources help subsequent sessions stay useful.

To resume in a new session, ask:

> Continue my learning path on retries. Read my progress and learning records, then resume the
> next step.

The agent reads the learning path bead and the topic's learning records, checks parked concepts,
and continues at the next owed step. It may ask a recall question to check retention rather than
repeat onboarding or assume that an earlier explanation is still understood.

## Park a Question While Working

During implementation, you can save a question without switching into a teaching session:

> Park this for learning: why does retrying this operation require an idempotency key?

The agent finds or creates a `learn: <topic> backlog` learning backlog bead and adds one comment
for that concept. The comment records the question, any answer so far, and where it came up.
Each concept has its own comment so several questions remain easy to distinguish.

When teaching resumes, the agent reads the comments and helps you turn the concepts into
lesson-sized steps. Outcomes such as “folded into step 2,” “taught,” or “dropped” are new comments
that reference the original comment. Corrections preserve the earlier comment too. Concepts
parked in Notes by older skill versions are also read.

## Keep Learning Separate from Implementation

Each project has one persistent **Learning epic**. Its children are the topic's learning path
beads and learning backlog beads. The epic and children all carry the `learning` label.

The epic groups learning for browsing. **Every child must also stay deferred** to keep it off
Beads' `bd ready` implementation queue. Deferring the parent does not defer its children.
The execution skill additionally skips learning-labelled items as a fallback.

You can inspect the state with Beads:

```bash
bd list --label learning --json
bd comments <backlog-id> --json
bd defer <learning-child-id>
bd ready --json
```

Dotbrain's skills maintain this state through Beads; it is not a separate Dotbrain learning CLI.
When a project has no execution engine, paths stay in conversation and concepts are not parked
as beads.

## Capture a Lesson When It Helps

Teaching does not automatically produce a lesson. After learning something useful, ask:

> Capture what we learned as a lesson, with a short reference and a retrieval exercise.

The agent proposes the title, topic, sections, questions, and sources for your approval before
writing. Lessons and references live in the Brain's `learning/` workspace alongside the mission,
preferences, glossary, resources, and learning records. Code-dependent explanations link to the
repository at the commit they were checked against.

All of this material stays in your private Brain. A [Brain site](brain-site.md) can render it
locally and add a Learn sidebar, but a site is optional. Without one, a lesson is finished when
its Markdown and supporting links are complete. With a declared learning site, the agent follows
its publishing guide and runs its check. Committing or publishing still needs your authorization.

## Turn Learning into Public Project Docs

Learning can reveal project knowledge that would help other users or contributors: an unclear
setup step, a recovery procedure, or an explanation of how a feature works. As you work through
a topic with the agent, consider whether that knowledge belongs in the project's public docs.

Ask the agent to propose a public guide based on what you learned. Write it for that audience,
ground its claims in the project, and include only context suitable for public readers. Derive a
new document rather than copying a private lesson or learning record; private operating details
and sensitive context stay in the Brain.

For example, a lesson on diagnosing failed deliveries might lead to a public troubleshooting
guide with supported checks and recovery steps. The private lesson can retain your exercises and
project-specific context while the public guide helps anyone using the project.

Creating or publishing public documentation is a separate action from teaching. Agree the
audience and scope before drafting, and authorize committing or publishing separately.

The workflow is defined by the bundled [teach-me skill](skills.md#learning).
