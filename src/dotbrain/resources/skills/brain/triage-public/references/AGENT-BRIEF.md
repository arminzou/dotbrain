# Writing agent briefs

An agent brief is a structured comment posted on a public issue when it moves to `ready-for-agent`.
It is the **public-safe summary** of the planned work, so an external or AFK agent (or a human
contributor) can see what "ready" means without reading the private Brain.

The binding execution contract is the **private work item** in the engine (acceptance criteria,
design notes, dependencies), authored via `operate-execution`. The brief derives from it; when they
disagree, the work item wins. Keep the brief public-safe: no private Brain paths, ADR numbers, or
internal vocabulary that only makes sense inside the Brainspace.

## Principles

- **Durable over precise.** The issue may sit for weeks while the code changes. Describe interfaces,
  types, and behavioral contracts; never reference file paths or line numbers.
- **Behavioral, not procedural.** Say *what* the system should do, not *how* to implement it. The
  agent explores fresh and makes its own implementation calls.
- **Testable acceptance.** Every criterion must be independently verifiable. "Triage should work" is
  not a criterion; "`gh issue list --label needs-triage` returns classified issues" is.
- **Explicit scope.** State what is out of scope, to prevent gold-plating.

## Template

```markdown
## Agent Brief

**Category:** bug / enhancement
**Summary:** one line on what needs to happen

**Current behavior:** what happens now (the bug, or the status quo a feature builds on).
**Desired behavior:** what should happen after the work, including edge cases and errors.

**Key interfaces:**
- `TypeName` — what changes and why
- `functionName()` — current vs desired return

**Acceptance criteria:**
- [ ] specific, testable criterion
- [ ] specific, testable criterion

**Out of scope:**
- adjacent thing that should NOT be changed here
```

## Example (bug)

```markdown
## Agent Brief

**Category:** bug
**Summary:** Skill description truncation drops mid-word, producing broken output

**Current behavior:** Descriptions over 1024 chars are cut at exactly 1024, ending mid-word.
**Desired behavior:** Truncate at the last word boundary before 1024 chars and append "...".

**Key interfaces:**
- The logic that populates `SkillMetadata.description` — respect word boundaries (no type change)

**Acceptance criteria:**
- [ ] Descriptions under 1024 chars are unchanged
- [ ] Longer descriptions truncate at the last word boundary before 1024 chars
- [ ] Truncated descriptions end with "...", total length still <= 1024

**Out of scope:**
- Changing the 1024-char limit; multi-line descriptions
```
