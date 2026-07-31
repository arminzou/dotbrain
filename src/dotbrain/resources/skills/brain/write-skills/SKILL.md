---
name: write-skills
description: Create new agent skills or improve existing ones — invocation choice, description writing, information hierarchy, and pruning. Use when the user wants to create a new skill, or improve, rewrite, or audit an existing one.
---

# Write Skills

A skill exists to wrangle determinism out of a stochastic system. **Predictability** — the agent taking the same _process_ every run, not producing the same output — is the root virtue; every lever below serves it.

**Bold terms** are defined in [`references/GLOSSARY.md`](references/GLOSSARY.md); look them up there for the full meaning. The two workflows below are what you _do_; the reference sections after them are what the workflows lean on; the dotbrain sections at the end cover where a skill is stored, reached, and linked.

## Workflow A — Creating a new skill

1. **Gather requirements** — the task/domain, the distinct **branches** it must handle, and whether it needs a deterministic **script** or only instructions.
2. **Choose invocation** — **model-invoked** is the default only if the agent must reach the skill unprompted (it costs **context load**); otherwise make it **user-invoked** (`disable-model-invocation: true`), paying **cognitive load** instead. See _Invocation_.
3. **Draft `SKILL.md`** — **steps** in order, each ending on a checkable **completion criterion**. Inline the **in-skill reference** every branch needs; push what only some branches reach into **external reference** under `references/`, starter files into `templates/`, deterministic operations into `scripts/`. See _Information hierarchy_.
4. **Write the description** (model-invoked only) — front-load the **leading word**; one trigger per **branch**; cut identity the body already covers. See _Writing the description_.
5. **Review with the user** — does it cover the branches? Anything missing or unclear?
6. **Suggest linking** — do not run it. Offer the command scoped to where the skill belongs. See _Scoping and linking_.

## Workflow B — Improving an existing skill

1. **Read** the current `SKILL.md` and any disclosed sibling files. Run it against the _Review checklist_.
2. **Patch in place** unless the structure itself is broken — targeted edits over full rewrites, and prefer positive phrasing over **negation**.
3. **Re-verify** against the checklist, then suggest the relink command matching the skill's existing scope.

## Invocation

Two choices, trading different costs:

- A **model-invoked** skill keeps a **description**, so the agent can fire it autonomously _and_ other skills can reach it (you can still type its name too). It contributes to **context load** — the description sits in the window every turn. Write a model-facing description with rich trigger phrasing ("Use when the user wants…, mentions…").
- A **user-invoked** skill strips the description from the agent's reach: only you, typing its name, can invoke it — and no other skill can. Zero context load, but it spends **cognitive load**: _you_ are the index that must remember it exists. Its `description` becomes human-facing — a one-line summary, trigger lists stripped.

### Declaring it in both runtimes

dotbrain links one skill directory into both `~/.claude/skills` and `~/.codex/skills`, so the choice
has to be stated twice. **The two keys are inverted**, and a boolean copied from one to the other
means the opposite of what it did:

| Runtime | Where | Model-invoked | User-invoked |
|---|---|---|---|
| Claude Code | `SKILL.md` frontmatter | omit the key | `disable-model-invocation: true` |
| Codex | `agents/openai.yaml` | omit `policy` (defaults true) | `policy.allow_implicit_invocation: false` |

Declaring only one leaves the skill user-invoked in that runtime and still auto-firing in the other,
which is the failure you will not notice, because the runtime you tested is the one you fixed.

`agents/openai.yaml` also carries Codex's human-facing `interface.display_name` and
`interface.short_description` (25–64 characters). For a user-invoked skill that pair is what the
operator actually reads when scanning the Codex skill list, so it does the job the stripped
`description` no longer does.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If it only ever fires by hand, make it user-invoked and pay no context load.

When user-invoked skills multiply past what you can remember, that piled-up cognitive load is cured by a **router skill**: one user-invoked skill that names the others and when to reach for each.

## Writing the description

A model-invoked **description** does two jobs — state what the skill is, and list the **branches** that should trigger it. Every word increases **context load**, so a description earns even harder pruning than the body:

- **Front-load the skill's leading word** — the description is where it does its invocation work.
- **One trigger per branch.** Synonyms that rename a single branch are **duplication** — "build features using TDD … asks for test-first development" is one branch written twice. Collapse them; keep only genuinely distinct branches.
- **Cut identity that's already in the body.** Keep the description to triggers, plus any "when another skill needs…" reach clause.

## Information hierarchy

A skill is built from two content types — **steps** and **reference** — that mix freely: a skill can be all steps, all reference, or both. The core decision is which to use and where each sits on the **information hierarchy**, a ladder ranked by how immediately the agent needs the material:

1. **In-skill step** — an ordered action in `SKILL.md`, the primary tier: what the agent does, in order. Each step ends on a **completion criterion**, the condition that tells the agent the work is done. Make it _checkable_ (can the agent tell done from not-done?) and, where it matters, _exhaustive_ ("every modified model accounted for", not "produce a change list") — a vague criterion invites **premature completion**.
2. **In-skill reference** — a definition, rule, or fact in `SKILL.md`, consulted on demand. Often a legitimately flat peer-set (every rule of a review on one rung) — a fine arrangement, not a smell.
3. **External reference** — reference pushed out of `SKILL.md` into a separate file, reached by a **context pointer**, loaded only when the pointer fires. (Spans _disclosed_ reference — a sibling file like this skill's `GLOSSARY.md`, still part of the skill — through fully **external reference** that lives outside the skill system and any skill can point at.)

A demanding completion criterion drives thorough **legwork** — the digging the agent does within the work — whether the skill has steps or not, since "every rule applied" binds flat reference just as "every step done" binds a sequence.

Push too little down and the top bloats; push too much and you hide material the agent actually needs. That tension is the whole decision.

**Progressive disclosure** is the move down the ladder — out of `SKILL.md` into a linked file — so the top stays legible. Mechanics: a linked `.md` file in the skill folder, named for what it holds. Some skills are used in more than one way, and each distinct way is a **branch** — different runs taking different paths through the skill. Branching is the cleanest disclosure test: inline what every branch needs, and push behind a pointer what only some branches reach. A **context pointer**'s _wording_, not its target, decides when and how reliably the agent reaches the material.

Where the ladder decides _how far down_ a piece sits, **co-location** decides _what sits beside it_ once there: keep a concept's definition, rules, and caveats under one heading rather than scattered, so reading one part brings its neighbours with it.

## When to split

**Granularity** is how finely you divide skills, and each cut spends one of the two loads, so split only when the cut earns it. Two cuts:

- **By invocation** — split off a **model-invoked** skill when you have a distinct **leading word** that should trigger it on its own, or another skill must reach it. You pay **context load** for the new always-loaded **description**, so that independent reach has to be worth it.
- **By sequence** — split a run of **steps** when the steps still ahead (a step's **post-completion steps**) tempt the agent to rush the one in front of it (**premature completion**). Keeping them out of view encourages the agent to do more **legwork** on the current task.

## Pruning

Keep each meaning in a **single source of truth**: one authoritative place, so changing the behaviour is a one-place edit.

Check every line for **relevance**: does it still bear on what the skill does?

Then hunt **no-ops** sentence by sentence, not just line by line: run the no-op test on each sentence in isolation, and when one fails, delete the whole sentence rather than trim words from it. Be aggressive — most prose that fails should go, not be rewritten.

## Leading words

A **leading word** is a compact concept already living in the model's pretraining that the agent thinks with while running the skill (e.g. _lesson_, _fog of war_, _tracer bullets_). Repeated throughout the text (though not necessarily — a strong leading word might only be needed once), it accumulates a distributed definition and anchors a whole region of behaviour in the fewest tokens, by recruiting priors the model already holds.

It serves predictability twice. In the body it anchors _execution_: the agent reaches for the same behaviour every time the word appears. In the description it anchors _invocation_: when the same word lives in your prompts, docs, and code, the agent links that shared language to the skill and fires it more reliably.

Hunt for opportunities to refactor skills to use leading words. A triad spelled out at three sites (**duplication**), a description spending a sentence to gesture at one idea — each is a passage begging to collapse into a single token. Examples:

- "fast, deterministic, low-overhead" -> _tight_ — one quality restated across a phase — into a single pretrained word (a _tight_ loop).
- "a loop you believe in" -> _red_ — converts a fuzzy gate into a binary observable state (the loop goes _red_ on the bug, or it doesn't).

You win twice over: fewer tokens, _and_ a sharper hook for the agent to hang its thinking on. Assume every skill is carrying restatements that leading words retire — go find them.

## Failure modes

Use these to diagnose issues the user may be having with the skill.

- **Premature completion** — ending a step before it's genuinely done, attention slipping to _being done_. Defence, in order: sharpen the completion criterion first (cheap, local); only if it is irreducibly fuzzy _and_ you observe the rush, hide the post-completion steps by splitting (the sequence cut).
- **Duplication** — the same meaning in more than one place. Costs maintenance and tokens, and inflates a meaning's prominence on the ladder past its real rank.
- **Sediment** — stale layers that settle because adding feels safe and removing feels risky. The default fate of any skill without a pruning discipline.
- **Sprawl** — a skill simply too long, even when every line is live and unique. Hurts readability and maintainability and wastes tokens. The cure is the ladder: disclose **reference** behind pointers, and split by **branch** or sequence so each path carries only what it needs.
- **No-op** — a line the model already obeys by default, so you pay load to say nothing. The test: does it change behaviour versus the default? A weak leading word (_be thorough_ when the agent is already thorough-ish) is a no-op; the fix is a stronger word (_relentless_), not a different technique.
- **Negation** — steering by prohibition backfires: _don't think of an elephant_ names the elephant and makes it more available, not less. Prompt the positive — state the target behaviour so the banned one is never spoken; keep a prohibition only as a hard guardrail you can't phrase positively, and even then pair it with what to do instead.

## Skill structure

dotbrain skills live in the data root under `skills/<bucket>/<name>/`. A skill folder:

```
skill-name/
├── SKILL.md      # required — steps + the reference every branch needs
├── references/   # disclosed reference: session detail, knowledge banks, API excerpts
├── templates/    # starter files meant to be copied and modified
└── scripts/      # deterministic scripts the skill can invoke directly
```

Name each file under `references/` for what it holds (this skill's own [`references/GLOSSARY.md`](references/GLOSSARY.md)).

## Scoping and linking

A **bucket** (`skills/<bucket>/`) is storage-only grouping; it does not decide a skill's reach. Reach is one of two classes:

- **Brain-coupled skill** — subject matter is operating the brain system itself (this skill is one). Packaged in the `brain/` bucket and force-wired into every project via `core.yaml` (`global_required` for `wire-brain`, `project_required` for the rest). Adopters cannot remove them. New Brain-coupled skills are a product decision, added to `core.yaml`.
- **Personal skill** — operator-owned and opt-in, in any other bucket. Reached only when the operator lists it: `global_extra:` in `skills/skills.yaml` (every session) or a project's `project.yaml` `skills:` list (one Brainspace).

Materialise a declaration with **linking**: `dotbrain skills link --scope global` for a personal global skill, `--scope project --project <name>` for one scoped to a single Brainspace. Linking is idempotent — it creates missing symlinks and prunes deselected ones. Suggest the command scoped to where the skill belongs; never run it automatically.

## Review checklist

- [ ] Invocation matches intent — **model-invoked** only if the agent should fire it unprompted — and declared in both runtime formats, whose keys are inverted
- [ ] Description (model-invoked): **leading word** front-loaded, one trigger per **branch**, no **duplication** with the body
- [ ] **Steps** end on checkable **completion criteria** — a vague one invites **premature completion**
- [ ] In-file content is only what every **branch** needs; the rest is **external reference**, `templates/`, or `scripts/`
- [ ] Each meaning has a **single source of truth** — no **duplication** across files
- [ ] Every line still **relevant** — no stale **sediment**, no **no-ops**
- [ ] Restated phrases collapsed into pretrained **leading words** where one fits
- [ ] Steering is positive, not **negation** — target behaviour stated; prohibitions only as hard guardrails, paired with what to do instead
- [ ] Linking command suggested to the user, scoped to where the skill belongs (not run automatically)
