---
name: review-architecture
description: Review a codebase for deepening opportunities, informed by the project Brain's domain language and ADRs.
disable-model-invocation: true
---

# Architecture Review

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Boundaries

- **vs `find-unknowns`**: that hunts comprehension gaps and assumes you do not yet understand the
  domain; this hunts structural depth problems and assumes you do. Orient first, review second.
- **vs `grill-decisions`**: that grills a plan against domain vocabulary. Step 3 here is a grilling
  too, but scoped to one deepening candidate and conducted in architecture vocabulary.
- **vs `to-design`**: this surfaces and shapes a refactor; that formalizes it. A candidate large
  enough to need slices graduates to a design doc rather than growing inside this skill.

This reviews structure, not a diff: it reads the codebase as it stands rather than the change in
front of it, and it proposes deepening rather than hunting defects.

This skill is an entry point rather than a pipeline stage. It starts from the codebase instead of
from a plan, and anything multi-step it produces joins the main pipeline at `to-design`.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [language](references/language.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Deepening a cluster safely depends on what it depends on: [deepening](references/deepening.md) covers the
dependency categories, seam discipline, and replace-don't-layer testing.

Key principles (see [language](references/language.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; ADRs record decisions the skill should not re-litigate.

## Process

### 1. Explore

**Scope before you scan.** Deepening a module pays off by making future changes to it cheaper, so a
candidate in code nobody touches is a refactor that never pays back. Decide *where* to look before
you look:

- If the user named a direction — a module, a subsystem, a pain point — take it and skip the
  inference below.
- Otherwise walk back a good stretch of `git log --oneline` to find the codebase's hot spots, the
  files and areas that keep coming up, and let those paths pull your attention first.
- If the changes are scattered with no clear hot spot, widen the net.

Read the project's domain glossary and any ADRs in the area you're touching first.

Then explore the codebase with local search/read tools. If a multi-agent explore tool is available,
use it for broad scans; otherwise inspect directly. Don't follow rigid heuristics — explore
organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

Completion: the scope is stated with the reason it was chosen, every module you flagged as shallow
has been through the deletion test, and you can name the ADRs covering the area you explored.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and also in how tests would improve
- **Strength** — `Strong`, `Worth exploring`, or `Speculative`

Rating each candidate forces the list to differentiate. A flat list where everything reads as
equally worth doing pushes the choice back onto the user with no information attached.

**Use CONTEXT.md vocabulary for the domain, and [language](references/language.md) vocabulary for the architecture.** If `CONTEXT.md` defines "Order," talk about "the Order intake module" — not "the FooBarHandler," and not "the Order service."

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly (e.g. _"contradicts that ADR — but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

Close with a **top recommendation**: which candidate you would tackle first and why. Be opinionated;
the user wants a strong read, not a menu.

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

Completion: every candidate carries all five fields, uses `CONTEXT.md` and the [language reference](references/language.md)
vocabulary, and any ADR conflict is marked. A top recommendation is named, and the user has been
asked to pick.

### 3. Grilling loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `CONTEXT.md`?** Add the term to `CONTEXT.md` — same discipline as `/grill-decisions` (see [context format](../grill-decisions/references/context-format.md)). Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `CONTEXT.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Apply the three-part test in [ADR format](../grill-decisions/references/adr-format.md), which is the single source for when any skill offers an ADR — a rejection that fails it ("not worth it right now") is ephemeral, not durable.
- **Want to explore alternative interfaces for the deepened module?** See [interface design](references/interface-design.md).

Completion: the picked candidate has an agreed shape, every new concept it names is in
`CONTEXT.md`, and any load-bearing rejection was offered as an ADR.
