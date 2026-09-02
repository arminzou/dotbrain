---
name: write-agent-docs
description: Supplies the writing discipline for any document an agent consumes — context pointers, information hierarchy, completion criteria, leading words, pruning. Use when creating or editing AGENTS.md or CLAUDE.md, public project docs agents rely on, Brain context, design or ADR docs, skills, or referenced guidance.
---

# Writing for agents

Use this reference for any document an agent consumes: public project documentation, an
`AGENTS.md` or `CLAUDE.md`, private Brain material, a skill, or a document reached through a
pointer. Their packaging and visibility differ; the writing does not. The goal is predictable
behaviour: the agent takes the same process each run, even when its exact output varies.

When the document is a skill, use the runtime's available skill-authoring capability for packaging,
invocation policy, and validation. Apply the writing principles here to its instructions and
references.

## Context pointers

A **context pointer** is text already in context that names material outside the current context and
states when to read it. A skill description is a pointer. So is an `AGENTS.md` line directing an
agent to an architecture document or private Brain file.

The pointer's wording, rather than its target, determines whether the agent retrieves the material
at the right time. A required document behind a vague pointer is a variance bug: sharpen the
pointer first, and inline the material only when a precise pointer still proves unreliable.

A pointer does two jobs: identify the material and name the distinct **branches** that should
trigger it. Every word in an always-loaded pointer costs attention on every turn, so:

- Front-load the concept that should trigger retrieval.
- Keep one trigger per genuine branch; collapse synonyms that describe the same case.
- Leave identity and explanation in the target document instead of repeating them in the pointer.

## The two loads

Every document and pointer spends one of two budgets:

- **Context load** is the cost of material kept in the agent's context every turn, including
  `AGENTS.md` instructions and skill descriptions.
- **Cognitive load** is the cost to the person who must remember which documents exist and when to
  invoke them. It is the price of retaining human judgement, not a cost that must always be removed.

Material reached through a pointer avoids most context load at the cost of the pointer itself.
Material with no pointer depends entirely on human discovery. Choose deliberately according to who
must notice the material and when.

## Information hierarchy

Agent documents contain two kinds of material: **steps**, which prescribe ordered action, and
**reference**, which supplies definitions, rules, or facts. A document can contain either or both.
Place each piece according to how immediately the agent needs it:

1. **In-file steps** are the primary tier: actions the agent must perform in order.
2. **In-file reference** supports every path through those actions or forms the document's main
   body when the document is itself a reference.
3. **Disclosed reference** sits in another file and is loaded only when a pointer's condition fires.

Push too little down and the main document sprawls. Push too much down and the agent misses material
it needs. Branching is the useful test: keep what every branch needs in the main file and disclose
what only some branches need.

**Co-location** applies within each tier. Keep a concept's definition, rules, and caveats together
so reading one brings the others into attention. Scattering fragments one meaning across a file;
duplication repeats the same meaning in several places. Both make behaviour less predictable.

**Sprawl** is length even when every line is current and unique. It thins attention and increases
maintenance. Cure it by restoring the hierarchy: disclose branch-specific reference and split only
where a real context boundary improves the work.

## Steps and completion criteria

Every ordered step needs a **completion criterion**: the condition that tells the agent the action
is genuinely finished.

- **Clarity:** the agent can distinguish done from not done. A vague bound invites premature
  completion as attention moves toward later visible steps. Sharpen the criterion before splitting
  the sequence.
- **Demand:** the criterion requires enough legwork. “Every modified model accounted for” produces
  a stronger investigation than “produce a change list.”

The strongest criteria are both checkable and exhaustive. When a criterion cannot be made clear
and later steps demonstrably pull attention away, split at a real context boundary such as a
handoff. Merely adding another heading does not hide the later work.

## Leading words

A **leading word** is a compact, established concept the agent can think with while following a
document. It recruits existing meaning instead of repeatedly spelling out the same behaviour. In a
pointer it improves retrieval; in the body it anchors execution.

Prefer an existing word with useful prior meaning over an invented label that needs its own long
definition. Repeat the word where the concept recurs, not the explanation behind it. A weak phrase
such as “be thorough” may change nothing; a sharper concept should name observable behaviour.

Negation works against this economy because it brings the prohibited concept into attention.
Describe the positive target. Keep a prohibition only when it protects a real boundary, and pair it
with the action the agent should take instead.

## Pruning

- Keep each meaning in a **single source of truth**. Link to the authority rather than maintaining a
  second explanation that can drift.
- Treat the environment as a source of truth too. Commands, schemas, configuration, and directory
  layout can often be inspected directly. Document the convention, rationale, or hazard that the
  environment cannot reveal; avoid caching easy lookups in prose.
- Remove **sediment**: material that was once relevant but no longer affects the document's job.
- Test each sentence for effect. A **no-op** that the agent already follows by default spends
  attention without changing behaviour; delete it rather than polishing it.
- Preserve deliberate repetition of a leading word, but remove duplicated explanations.

## Dotbrain documents

When writing in a dotbrain-wired project, private Brain, or `$DOTBRAIN_HOME`, read
[Writing within dotbrain](references/dotbrain-skills.md) for placement, public/private boundaries, and the
workflows that own document structure and lifecycle.
