# Simplify review

A simplify review asks one question of a change: what could it do without? It names code and
instructions the change could delete, collapse, or hand to something that already exists. It is
not a correctness review. `review-gate` owns who may run it, the review bead, and closeout; this
file is the procedure the reviewer follows.

## Before reporting

- Read the review target and trace what the change does end to end. A cut proposed from a skim
  is often a second bug.
- For each candidate cut, find what would replace it: search the repository for an existing
  helper or rule, and confirm the replacement covers every behavior the change needs.

## What to look for

Tag each finding with the kind of cut:

- `delete:` nothing needs it: a dead path, an option no caller sets, a feature built ahead of
  any use. Nothing replaces it.
- `reuse:` the repository already has it. Name the path of the existing helper, pattern, or rule.
- `stdlib:` the language's standard library ships it. Name the function.
- `native:` the platform, runtime, or an already-installed dependency does it. Name the feature.
- `yagni:` an abstraction, setting, or layer with a single use. Say what to inline.
- `shrink:` the same behavior in fewer lines. Show the shorter form.

## Instructions and prose

Much of a change can be instructions an agent follows: skills, references, prompts, and agent
definitions. Simplify them the same way:

- A rule that restates one another skill or reference owns is `reuse:`; point to the owner.
- A section that repeats the shared contract, or guidance no agent can act on, is `delete:`.
- A paragraph that explains where a single rule would do is `shrink:`.

Do not cut a rule only because it is long. Check first whether anything else enforces it.

## Report

One numbered line per finding, so the requester can say which to act on:

```text
<n>. <path>:<line or range>: <tag> <what to cut>. <what replaces it>.
```

For example:

```text
1. src/cache.py:12-40: stdlib: hand-written LRU dictionary. functools.lru_cache(maxsize=256).
2. src/api/client.ts:8: native: an HTTP library imported for two GET calls. fetch.
3. src/export.py:55-70: reuse: CSV quoting duplicates write_rows in src/util/csv.py. Call it.
4. src/store.py:20-61: yagni: StorageBackend interface with one implementation. Use the class.
5. plugin/skills/example/SKILL.md:30-38: reuse: restates the claim rule run-execution owns. Link to it.
```

End with `net: -<N> lines possible.`, counting only the findings listed. When there is nothing
to cut, write `No simplification findings.` and stop. Report no approval verdict: a simplify
result neither passes nor blocks a change.

## Keep out of scope

- Correctness, security, and performance belong to code review. If you notice a problem of that
  kind, list it under a separate `Outside simplify` heading so the lead can file it as discovered
  work; never drop it silently.
- Never propose cutting input validation at a trust boundary, protection against data loss,
  security measures, accessibility, explicitly required behavior, or the one smoke test or
  self-check that proves a piece of logic works.
- List findings only and do not apply fixes. Findings never block delivery and are never applied
  inside a handoff loop; `review-gate` records them in the separate simplify review bead.
