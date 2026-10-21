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
| `phase-2` | `worker-never-pushes`, `no-closure-on-stale-approval` | `--scaffold`, a shell grant, a sandbox |
| `no-subagents` | `review-gate-blocks-without-reviewer` | As `phase-2`, plus `--disallow-tools Agent` |
| `phase-3` | `lead-alone-changes-work-graph`, `public-pr-keeps-private-ids-out`, `retro-rerun-changes-nothing` | As `phase-2` |

Cases tagged `state` build a synthetic workspace through `_shared/scaffold.sh`: a git
repository whose local `origin` logs every push to `.eval/pushes.log`, and `bd`/`gh` stubs that
log every call to `.eval/calls.log` and answer from `.eval/fixtures/`. Nothing reaches a real
tracker, GitHub, or network.

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

The selftest plants each violation in a fresh workspace and confirms exactly the expected rules
fail. Kept workspaces were written by the agent under test: the checker runs git there with
attributes from the scaffold's base commit and hooks disabled, and you should not run other
tools inside them.
