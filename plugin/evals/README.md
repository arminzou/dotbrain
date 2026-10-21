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
| `phase-2` | `worker-never-pushes`, `no-closure-on-stale-approval`, `review-gate-blocks-without-reviewer` | `--scaffold`, a shell grant, a sandbox |
| `phase-3` | `lead-alone-changes-work-graph`, `public-pr-keeps-private-ids-out`, `retro-rerun-changes-nothing` | `--scaffold`, a shell grant, a sandbox |

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

```bash
claude plugin eval . --ablation none --runs 3 --no-publish --scaffold --keep-temp \
  --allow-tools Bash Write Edit --tag phase-2 phase-3
```

Run `review-gate-blocks-without-reviewer` on its own with `--disallow-tools Agent`, since that
grant applies to the whole run and other cases dispatch subagents.

Use `--ablation none`: skill-loading graders count only in a single-arm run. Pass
`--max-cost-usd` to cap spend, and keep `--no-publish` so reports stay local.

## Checking state the graders cannot see

Native graders read the transcript and files. Each state case also lists rules in its `checks`
file for `_shared/check.py`, which reads a kept workspace (`--keep-temp`) and prints JSON:

```bash
python3 -I _shared/check.py <kept-workspace> $(cat <case>/checks)
python3 -I _shared/check.py --selftest
```

The selftest plants each violation in a fresh workspace and confirms exactly the expected rules
fail. Kept workspaces were written by the agent under test: the checker runs git there with
attributes from the scaffold's base commit and hooks disabled, and you should not run other
tools inside them.
