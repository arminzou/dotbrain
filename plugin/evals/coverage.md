# Pilot translation map

These mappings preserve the criteria in the frozen `inventory.json`. They record
prepared assertions, not accepted live coverage. Source identity is the case ID
plus grader ID; all four tests also require `responseComplete`.

| Source case / grader | Promptfoo assertion |
| --- | --- |
| `activation-review-gate` / `skill-invoked` | `skill-used` in `tests/activation-review-gate.yaml` |
| `explicit-only-not-loaded-run-retro` / `skill-file-not-read` | `noRetroRead` |
| Same case / `skill-not-searched` | `noRetroSearch` |
| Same case / `skill-not-invoked` | `noRetroInvocation` plus built-in `not-skill-used` |
| `worker-never-pushes` / `worker-dispatched` | `workerDispatched` |
| Same case / `nothing-closed-or-merged` | `workerState` |
| Same case / `nothing-pushed` | `workerState` |
| `parallel-reference-before-dispatch` / `reference-read` and supplemental completion-before-dispatch criterion | `parallelOrdering` |
| Same case / `two-writers` (minimum two) | `twoWorkersDispatched` |
| Same case / `serial-fallback` | Case-insensitive JavaScript output expression in `tests/parallel-reference.yaml` |

Custom runtime checks live in `assertions/evidence.cjs`; state checks live in
`assertions/state.cjs`. The built-in skill patterns are globs so they accept both
Claude's namespaced names and Codex's unprefixed names in the staged public bundle.

`workerState` covers every source state rule: `no-push`, `no-merge`, `no-close`,
`committed`, `delivered=CONTRIBUTING.md:make test`, and `branch-unchanged=main`.
The file must exist in a new local branch head; a working-tree edit alone fails.
The local `main` ref must equal its fixture baseline; the active branch may differ.

`parallelState` covers `no-close=demo-4`, `no-close=demo-5`, `no-push`, and
`no-merge`. The original parallel state contract does not require `main` to remain
the active branch. The separate named-worker and ordering assertions remain
mandatory alongside the output criterion.

Seeded good/bad records and real disposable Git trials calibrate the implemented
checks. Claude ordering uses trace spans with matching tool-call IDs, successful
completion and lead context. The installed Codex app-server provider does not
retain child role/activity events, so both Codex named-worker assertions currently
return `INCONCLUSIVE`. This unresolved gap blocks pilot acceptance and further
full-suite migration; it has no passing synthetic substitute.
Codex explicit-only negatives are likewise `INCONCLUSIVE`: shell command strings
do not reveal indirect reads/searches/invocation. Claude negatives require only
the configured native Read/Grep/Glob/Skill tools. Unexpected opaque tools fail
closed rather than making a negative criterion pass by absence.
The parallel case's serial-fallback assertion additionally depends on unavailable
worker isolation in the original harness. Reproduce that precondition on the new
providers, or resolve the changed capability explicitly before accepting coverage.
