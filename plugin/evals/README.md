# Plugin evals

These cases check dotbrain's skill rules as agent behavior with
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals): each run is a fresh,
headless Claude Code session with only this plugin loaded, graded on what the agent did.
Runs are paid and nondeterministic, so they run locally before a release that changes a
rule-bearing skill. They do not run in CI.

## Cases

| Tag | Cases | Needs |
| --- | --- | --- |
| `phase-1` | `explicit-only-not-loaded-*`, `activation-*`, `no-skill-for-unrelated-request` | Nothing beyond Claude Code |
| `phase-2` | `worker-never-pushes`, `no-closure-on-stale-approval`, `closure-on-fresh-approval`, `review-gate-lead-reviews-worker-change` | `--scaffold`, a shell grant, a sandbox |
| `no-subagents` | `review-gate-blocks-self-review` | As `phase-2`, plus `--disallow-tools Agent`; see the note below |
| `phase-3` | `lead-alone-changes-work-graph`, `public-pr-keeps-private-ids-out`, `retro-rerun-changes-nothing`, `retro-records-new-evidence` | As `phase-2`. The harness gives subagents no worktree isolation, so delegation runs workers one at a time |
| `execution-rules` | `parallel-reference-before-dispatch`, `execution-recovery-boundaries`, `parallel-group-promotion`, `execution-role-routing` | The first uses the state scaffold; others are decision exercises |
| `workflow-owners` | `final-review-coverage-and-dispositions`, `handoff-stop-scopes`, `metadata-preserves-checkpoint-state` | Decision exercises; no host or tracker writes |
| `workflow-owners` | `accepted-head-before-delivery` | Decision exercise for promotion, each reviewed-branch push, PR readiness, and check failure; unrun |
| `goal-shortfalls` | `goal-shortfall-blocks-final-review`, `handoff-goal-shortfall-final-review`, `unreported-automatic-failure-is-high`, `automatic-failure-blocks-later-runs`, `handoff-admits-goal-shortfall-within-budget`, `accepted-automatic-failure-mode` | State scaffold except the accepted-mode decision exercise; cases unrun |

Cases tagged `state` build a synthetic workspace through `_shared/scaffold.sh`: a git
repository whose local `origin` logs every push to `.eval/pushes.log`, and `bd`/`gh` stubs that
log every call to `.eval/calls.log` and answer from `.eval/fixtures/`. Nothing reaches a real
tracker, GitHub, or network.

The `execution-rules` and `workflow-owners` cases cover moved workflow instructions.
For `accepted-head-before-delivery`, inspect the kept transcript against both graders'
ordering and failure rules as well as the native patterns; patterns alone are not a pass.
Decision exercises check the agent's selected next operations; they do not qualify
runtime concurrency. For `parallel-reference-before-dispatch`, also inspect the
kept transcript: the Read of `parallel-execution.md` must precede the first writing
worker's Agent call. The native tool-presence and response graders alone cannot prove
that ordering. All new cases remain unrun until a paid eval is authorized separately.

## Running

From `plugin/`:

```bash
claude plugin eval . --ablation none --runs 3 --no-publish --tag phase-1
```

State cases grant a shell, which Claude Code runs only inside its OS sandbox: use Linux
(with `bubblewrap` and `socat`), macOS, or WSL2. Native Windows has no sandbox backend.
`--tag` takes several tags and runs a case that has any of them.

```bash
claude plugin eval . --ablation none --runs 3 --no-publish --scaffold --keep-temp \
  --allow-tools Bash Write Edit --tag phase-2 phase-3
claude plugin eval . --ablation none --runs 3 --no-publish --scaffold --keep-temp \
  --allow-tools Bash Write Edit --disallow-tools Agent --tag no-subagents
```

On Windows, run every case under WSL2: it is the only setup there that can run them all, and
running the suite twice on one machine shows no OS difference. The state cases have been run
with Claude Code 2.1.283 under WSL2.

The runner refuses every Bash-granting run when `~/.docker` holds a symbolic link, as Docker
Desktop's WSL integration creates. Setting `DOCKER_CONFIG` does not avoid this. Move
`~/.docker` aside for the run and restore it after.

Version matters here:

- **2.1.283:** has no `--disallow-tools`, and leaving `Agent` out of a case's `allowed_tools`
  does not remove it. So `review-gate-blocks-self-review` cannot run there in its intended
  mode: the agent can still dispatch an independent reviewer.
- **2.1.306 (WSL2):** has the flag, but its sandbox made the whole eval workspace read-only for
  shell commands, so no state case can run. That case stays unverified until a version offers
  both.
- **All versions:** the eval runner gives subagents no worktree isolation.

Run with `--ablation none`. In the default two-arm run, a `tool_used` grader on `Skill` only
reports whether the plugin fired and does not count toward the score, unless the grader sets
`arm: both`, as the explicit-only cases do. Pass `--max-cost-usd` to cap spend, and keep
`--no-publish` so reports stay local.

## Checking state the graders cannot see

Native graders read the transcript and files. A state case passes only when its native graders
and the rules in its `checks` file both pass. `_shared/check.py` (Python 3, git 2.40 or later)
reads a kept workspace (`--keep-temp`) and prints JSON:

```bash
python3 -I _shared/check.py <kept-workspace> --checks <case>/checks
python3 -I _shared/check.py --selftest
```

The checker requires a logged agent call before grading state: an ordinary `bd` or
`gh` call, or a Git command recorded by Git's built-in Trace2 logging to the same
`.eval/calls.log`. Shell initialization enables tracing alongside the stub PATH;
prompts need no harness instructions. This also covers a retrospective that only
reads Git. With no logged call, every rule fails (score 0): an empty log in a
read-only sandbox proves no must-not result. Stubs exit on log-write failure;
neither they nor Git rely on writing the sandboxed home. The external checker
disables tracing for its own Git reads, so it cannot supply this evidence.
Native graders alone are never a state-case pass.

The retro cases invoke `/dotbrain:run-retro` directly. Slash invocation loads the
skill without a `Skill` tool call, so these cases grade state rather than requiring
a `tool_used: Skill` record; `retro-rerun-changes-nothing` instead requires a logged Git
history read, so loading the skill and stopping does not pass. Their fixtures pre-seed the notebook lock and temporary
file exclusions because the sandbox cannot edit `.brain/.git/info/exclude`, so the skill's own
add-the-exclusions step is not exercised here.

The selftest plants each violation in a fresh workspace and confirms exactly the expected rules
fail. Kept workspaces were written by the agent under test: the checker runs git there with
attributes from the scaffold's base commit and hooks disabled, and you should not run other
tools inside them.
