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

Every state prompt first asks the agent to run `bd eval-health`. The stub appends a
health record only after a successful log write, and records later write errors in
the fresh temporary home. The checker fails every rule (score 0) if that probe is
missing or a write failed. This tests the agent's sandbox access, which may differ
from the external checker's access. Native graders alone are never a state-case pass.

The selftest plants each violation in a fresh workspace and confirms exactly the expected rules
fail. Kept workspaces were written by the agent under test: the checker runs git there with
attributes from the scaffold's base commit and hooks disabled, and you should not run other
tools inside them.
