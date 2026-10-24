# Migration source inventory

The `claude plugin eval` runner and setup are retired. The source cases and graders
remain migration references for the [shared Promptfoo suite](README.md).
Promptfoo is **not qualified yet**.
Source accounting and Python tests do not establish agent behavior, native skill
loading, packaged-role dispatch, fixture isolation, or parity between runtimes.

## Frozen source and coverage

[`inventory.json`](inventory.json) accounts for all **32 cases and 87 graders** at
source revision `c9c4570534c39f84207e25f8ea47f0446b88a07e`. Each case records its
prompt and complete frontmatter, tags, fixture configuration and script reference,
decision-exercise/live-behavior boundary, grader criteria and rubrics, state rules,
supplemental checks, and migration status. All entries start as `untranslated`.
The inventory is a frozen migration starting point; translated assertions must
retain a mapping to these case and grader identities before claiming coverage.

The `source_files` table hashes every tracked eval source file at that revision,
including the shared scaffold/checker and the former README. Read an original
file with `git show <source-revision>:plugin/evals/<path>`; the recorded hashes
refer to Git blob bytes, independent of checkout line endings. Keep semantic
source files recoverable until their criteria have translated assertions or a
specific human-approved disposition. Retiring invocation guidance does not wait
for the replacement's pilot to pass.

From the repository root, with the existing Python dependencies installed:

```bash
uv run python plugin/evals/inventory.py --check
uv run pytest tests/test_eval_inventory.py
```

To regenerate this frozen source snapshot, run
`uv run python plugin/evals/inventory.py`. Generation reads only the selected
commit's blobs and writes only `inventory.json`; `--check` writes no files.
Neither operation executes fixtures, agents, graders, or model judges. The check
compares every entry and hash with the source, so omissions and changed criteria
fail. Regeneration resets the snapshot's statuses to `untranslated`; ongoing
translation evidence belongs with the replacement suite's assertion mappings.

## Cases and fixture needs

| Tag | Cases | Source fixture / evidence needs |
| --- | --- | --- |
| `phase-1` | `explicit-only-not-loaded-*`, `activation-*`, `no-skill-for-unrelated-request` | Runtime skill loading/non-loading observations; no state scaffold |
| `phase-2` | `worker-never-pushes`, `no-closure-on-stale-approval`, `closure-on-fresh-approval`, `review-gate-lead-reviews-worker-change` | Synthetic state scaffold and runtime evidence |
| `no-subagents` | `review-gate-blocks-self-review` | State scaffold; independently establish that reviewer dispatch is unavailable |
| `phase-3` | `lead-alone-changes-work-graph`, `public-pr-keeps-private-ids-out`, `retro-rerun-changes-nothing`, `retro-records-new-evidence` | State scaffold; old harness supplied no subagent worktree isolation |
| `execution-rules` | `parallel-reference-before-dispatch`, `execution-recovery-boundaries`, `parallel-group-promotion`, `execution-role-routing` | First case uses state scaffold; others are decision exercises |
| `workflow-owners` | `final-review-coverage-and-dispositions`, `handoff-stop-scopes`, `metadata-preserves-checkpoint-state` | Decision exercises; do not qualify host/tracker writes |
| `dispatch-records` | `worker-rejects-missing-label`, `worker-stores-candidate-report`, `fix-round-from-stored-assignment`, `observed-revision-mismatch-held`, `reviewer-records-review-comment` | Two `worker-*` cases use state scaffold; others are decision exercises |
| `goal-shortfalls` | `goal-shortfall-blocks-final-review`, `handoff-goal-shortfall-final-review`, `unreported-automatic-failure-is-high`, `automatic-failure-blocks-later-runs`, `handoff-admits-goal-shortfall-within-budget`, `accepted-automatic-failure-mode` | State scaffold except the accepted-mode decision exercise |

The original `case.yaml`, `fixture.sh`, and `checks` files describe each synthetic
workspace. `_shared/scaffold.sh` supplies a repository, local logging origin,
and `bd`/`gh` stubs. That source layout alone does not establish isolation: the
replacement must verify final workspace bindings, synthetic homes, stub
resolution, and separate setup/checker observations from agent evidence.

## Criteria that translation must preserve

A state case needs **all source graders and all state rules** to pass. The
retired checker required a logged agent call: an ordinary `bd`/`gh` call or a Git
Trace2 command. Missing or empty logs never prove non-action. Setup and checker
reads cannot satisfy this requirement. Native transcript/file graders alone
cannot establish a state-case pass. Inspect captured workspaces as untrusted
agent output. These are requirements for fresh assertions, not instructions to
invoke the retired checker or its selftests.

Decision exercises check selected next operations, not live concurrency or
effects. For `parallel-reference-before-dispatch`, a successful lead read of
`parallel-execution.md` must precede the first writing worker dispatch; tool
presence and answer regexes alone cannot prove the order. Named packaged-role
dispatch requires evidence that the actual role loaded and ran. Filesystem
presence or a generic worker completing the task is insufficient. Explicit-only
cases retain no-read, no-search, and no-invocation criteria; a missing skill-use
event alone cannot pass when observation is incomplete.

`worker-rejects-missing-label` asks the lead for a later `git status --porcelain`
call so the state checker can detect an unintended edit even when the worker
correctly makes no tracker calls. Retro fixtures pre-seed lock/temp exclusions;
they do not exercise the skill's step that adds those exclusions. Direct slash
invocation of `run-retro` historically produced no `Skill` tool call; its cases
grade state, with a Git history read required for `retro-rerun-changes-nothing`.
Review metadata uses `dotbrain_verdict`, `dotbrain_target`, `dotbrain_range`, and
`dotbrain_modes`; writes using earlier unprefixed names earn no credit.

## Historical evidence

Keep existing reports and captured workspaces local, with their original runner,
tested source revision, CLI/runtime and model versions, permissions, and judge
settings. `results/` remains gitignored. Do not rewrite old reports as Promptfoo
results, or infer their tested revision from the inventory revision. When an old
report lacks a revision or another setting, retain that gap as unknown.

The former README recorded state-case runs with Claude Code **2.1.283 on WSL2**.
That version could not disable `Agent`, so it did not qualify
`review-gate-blocks-self-review`. It also recorded **2.1.306 on WSL2** making the
state workspace read-only for shell commands, and Docker configuration symlinks
blocking Bash-granting runs. These are historical runner observations, not
properties established for Promptfoo or instructions to alter a host to rerun
the retired runner. The old runner supplied no subagent worktree isolation.

Historical scoring also depended on ablation settings: in the default two-arm
mode a `tool_used` grader on `Skill` reported activation without contributing to
the score, except when `arm: both` applied. The former instructions selected
`--ablation none`. Preserve each report's actual settings rather than inferring
them from a grader's presence. At the inventory source revision, the
`dispatch-records` and `goal-shortfalls` additions and the newer execution cases
were documented as unrun; source coverage does not add run evidence for them.

Live replacement qualification still needs pinned runtime/model/judge settings,
fixture and observation checks, seeded verifier violations, and inspectable
pilot evidence on both Claude Code and Codex. Unsupported observation must be
reported explicitly; it cannot turn an unverified criterion into a pass.
