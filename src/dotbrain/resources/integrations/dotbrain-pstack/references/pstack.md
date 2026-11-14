# Pstack routing and explicit adaptations

Read the selected `source` from `.dotbrain-pstack.json`. Resolve paths below
against that checkout. The qualified baseline is pstack 0.15.36 at revision
`9cd6939b766cb920f1c44970d7c7ee1ec28bd0d6`; qualification of other revisions or
native environments is separate work. Dotbrain maintains this mode, not an
upstream pstack fork. Keep the dependency checkout unchanged.

This is the workflow entrypoint. Do not also invoke `poteto-mode`, its embedded
Feature/Shipping playbooks, or an unrelated globally installed copy: their task,
replacement, and authority procedures are not this mode's Beads contract.
The mappings below identify the adapted entrypoints instead of assuming a
top-level override will erase conflicts after a leaf has loaded.

## Compatible capabilities

Read each leaf before using its method. Conditional references inside that leaf
remain relative to its original directory; do not copy it into a new location.

| Need | External source |
| --- | --- |
| Understand behavior or motivation | `skills/how/SKILL.md`, `skills/why/SKILL.md` |
| Explore an unsettled shape | `skills/architect/SKILL.md`, `skills/arena/SKILL.md` |
| Reproduce a cheap, focused bug | `skills/tdd/SKILL.md` |
| Challenge a contested design | `skills/interrogate/SKILL.md` |
| Partition independent exploration/coverage | `skills/swarm/SKILL.md` |
| Clarify public prose | `skills/unslop/SKILL.md`, `skills/technical-writing/SKILL.md` |
| Keep verification tied to the actual artifact | `skills/principle-prove-it-works/SKILL.md` |
| Choose the smallest complete change | `skills/principle-laziness-protocol/SKILL.md` |
| Model data and shared ownership | `skills/principle-model-the-domain/SKILL.md`, `skills/principle-separate-before-serializing-shared-state/SKILL.md` |

Use native Agent/spawn tools for Cursor Task references. Outside Cursor, writing
work is local and isolated in wired Git worktrees. Keep exploration/review roles
read-only. Read configured pstack role lines from this harness's normal settings
location; use native supported models and the leaf's documented fallback. An
unavailable preferred family is a reported limitation, not authority to switch
providers or pretend a diverse review happened. Workers receive adopted context
and shape; they do not restart coordinator orchestration or spawn further
writers unless their assignment explicitly permits it.

## Adapted entrypoints

| Upstream procedure or conflict | This mode's executable route |
| --- | --- |
| Top-level Feature/Refactoring/Bug-fix procedures and durable todos | Use the main mode's scoped Beads selection, coordinator claim, local delegation and verification. Upstream step/throughput/architecture todos are temporary procedure inside a task; durable dependencies, unfinished work and evidence are Beads records. |
| Architecture/arena fan-out | The coordinator invokes these when a real shape needs exploration and passes ownership, scope and capacity. A worker forbidden to delegate implements the supplied shape and returns its evidence; it does not acquire an orchestration role. |
| Default cloud execution and `poteto-agent` | Use native general agents locally, with the delivered mode and bounded assignment. No packaged Dotbrain agents or remote private-context distribution. |
| Default fresh-agent replacement and transcript pickup | Use [ownership and recovery](continuity.md). Preserve the old writer/candidate, prove write authority ended, and guard coordinator transfer. Durable records lead; transcript access is supplementary and stays within the active project's authority. |
| Decision trails and committing ambitious logs | Keep the trail private through `maintain-brain`, or as a private working artifact linked from Beads. `skills/show-me-your-work/references/decision-log-template.tsv` supplies a format if useful. Do not invoke its transcript-mining/commit procedure automatically, commit private trails to code, or substitute a TSV for task state. Public review receives freshly derived rationale. |
| Comment cleanup's write/apply/delete-constraint wrapper | Do not invoke `no-comments` as an automatic edit runner. Its `skills/no-comments/references/comment-sicko.md` is an optional critique rubric for a strictly read-only reviewer. Turn proposed removals into findings; apply only authorized in-scope changes after checking actual contracts. Preserve required safety, legal and repository guidance. This mode does not delete an unenforced requirement merely because it is a comment. |
| Retrospectives and recurring-mistake correction | Capture verified project understanding with `maintain-brain`, adopted requirements with `repo-rules`, and pending enforcement with Beads. `skills/reflect/SKILL.md` is an explicit skill-edit proposal workflow, not automatic Brain maintenance. `skills/correct/SKILL.md` supplies an architecture/types/checks-first method when recurring correction is requested. Keep requirement tables in their repository owner, normally RULES.md, and AGENTS.md routing-only when required. Do not edit generated caches or the qualified upstream dependency. Skill/policy adoption still needs applicable authority; approved grants need no repeat approval. |
| External devex tickets, team messages, PRs and shipping/autopilot | Record private unfinished work in Beads. External mutations use the current explicit user/repository authority and identity. Mode opt-in and a green check grant neither publication nor merge. Prepare reviewable artifacts first, retain evidence, and record task versus PR/release outcomes separately. |

For absent control/deslop tools, use native terminal/browser inspection on the
actual changed surface and inspect the diff before committing, following
pstack's documented fallback. Do not install another provider or invent a
passing result. Keep fixes inside the requested scope. Inspection, review and
verification do not silently authorize enforcement or unrelated cleanup.

On a pstack upgrade, compare the referenced leaves and their conditional
resources with this table, resolve changed contracts, and rerun affected native
qualification. A clean revision inventory proves identity, not behavior.
