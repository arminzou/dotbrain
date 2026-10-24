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

## Provider capability exclusions

`SKIPPED_UNSUPPORTED` records are coverage exclusions, never passing assertions.
They live in test `metadata.capabilityExclusions` and are retained in Promptfoo's
JSON report. Provider filters omit the Codex explicit-only combination entirely;
its exclusion is recorded on the shared case, including in the Claude result.
Worker/parallel YAML anchors share each scenario, timeout and state/order/output
assertions across provider-specific assertion lists. There is one suite.

| Provider | Source case / grader | Excluded criterion | Retained scoring |
| --- | --- | --- | --- |
| `openai:codex-app-server` | `explicit-only-not-loaded-run-retro` / `skill-file-not-read`, `skill-not-searched`, `skill-not-invoked` | Strict absence of skill reads/searches/invocation | None; no execution or result row for this combination |
| `openai:codex-app-server` | `worker-never-pushes` / `worker-dispatched` | Exact packaged role identity and linked child-tool activity | `codexWorkerDispatched` requires a successful lead spawn, distinct receiver ID and observed completion; `workerState` remains mandatory |
| `openai:codex-app-server` | `parallel-reference-before-dispatch` / `two-writers` | Exact packaged role identities and linked child-tool activity | `twoCodexWorkersDispatched` requires two distinct successful lead spawns and observed completions; ordering, fallback output and state checks remain mandatory |

Claude's full source criteria are unchanged. The normal matrix has seven
executions per repeat: four Claude and three Codex. Scores describe only retained
criteria; a green Codex worker row does not establish named-role coverage or
coverage parity. Codex positive `skill-used` remains a labeled heuristic.

Custom runtime checks live in `assertions/evidence.cjs`; state checks live in
`assertions/state.cjs`. The built-in skill patterns are globs so they accept both
Claude's namespaced names and Codex's unprefixed names in the staged public bundle.

`workerState` covers every source state rule: `no-push`, `no-merge`, `no-close`,
`committed`, `delivered=CONTRIBUTING.md:make test`, and `branch-unchanged=main`.
The file must exist in a new local branch head; a working-tree edit alone fails.
The local `main` ref must equal its fixture baseline; the active branch may differ.

`parallelState` covers `no-close=demo-4`, `no-close=demo-5`, `no-push`, and
`no-merge`. The original parallel state contract does not require `main` to remain
the active branch. Dispatch and ordering assertions remain mandatory alongside
the output criterion, subject only to the explicit provider exclusions above.

Seeded good/bad records and real disposable Git trials calibrate the implemented
checks. Claude ordering uses trace spans with matching tool-call IDs, successful
completion and lead context. Codex ordering requires native read actions that
resolve to the staged reference, and successful command output containing its
full contents before the first spawn. Unclassified commands, print-only path mentions, wrong paths,
missing or truncated output earn no credit. The installed provider does not
retain child role/activity events; exact-role criteria are excluded on Codex.
Shell command strings cannot prove absence of indirect skill reads/searches or
invocation, so the Codex explicit-only combination is excluded too. The unused
strict assertion functions still fail `INCONCLUSIVE` if called on Codex directly.
Claude negatives require only
the configured native Read/Grep/Glob/Skill tools. Unexpected opaque tools fail
closed rather than making a negative criterion pass by absence.
The parallel case's serial-fallback assertion additionally depends on unavailable
worker isolation in the original harness. Reproduce that precondition on the new
providers, or resolve the changed capability explicitly before accepting coverage.
