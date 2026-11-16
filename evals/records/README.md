# Record placement

This eval checks the workflow-independent core with a stock skill workflow.
It runs pstack, with no adapter, in a small task-list repository over two cold
sessions:

1. **s1**: plan a multi-session feature, implement only its first part, commit, and stop.
2. **s2**: "Continue the due-date work from the last session."

The convention delivered by the session-start hook is the only dotbrain guidance.
Each runtime passes when every criterion holds:

| Criterion | Passes when |
| --- | --- |
| `sessions_ran` | Both sessions left a transcript with tool calls |
| `plan_in_beads` | The project tracker holds at least two issues |
| `no_repo_records` | The checkout gained no files outside `todo/`, `tests/` and `README.md`, tracked or untracked |
| `reasoning_in_brain` | The Brain gained or changed a record after setup |
| `resumed_from_beads` | s2 ran `bd ready`, `bd list` or `bd show` |
| `no_transcript_reads` | Neither session read a Claude or Codex transcript directory |

## Model-free calibration

```sh
cd evals/records && uv run python -B -m unittest -v test_records
```

A known-good record passes every criterion, and each known-wrong record fails
exactly its own. This calibrates the grader, not agent behavior.

## Native runs

Use a new root outside every wired checkout, one per runtime. `prepare` clones the
local pstack checkout into the root's private home, so nothing is downloaded:

```powershell
$root = Join-Path $env:USERPROFILE 'qualifications/records-claude'
uv run python evals/records/records.py prepare $root --pstack C:/src/pstack
```

Before the first session, sign in inside the root's isolated runtime home:
`home/claude` (`CLAUDE_CONFIG_DIR`) or `home/codex` (`CODEX_HOME`). For Codex,
also install the dotbrain plugin into `home/codex` and trust its hooks. Claude
receives the plugin from this checkout through `--plugin-dir`. To reuse a signed-in
home, pass `--runtime-home`; clear its earlier sessions and Codex memories between roots. On Windows, set
`CLAUDE_CODE_GIT_BASH_PATH` for headless Claude.

```powershell
uv run python evals/records/records.py run $root --runtime claude --session s1 --executable claude --allow-native
uv run python evals/records/records.py run $root --runtime claude --session s2 --executable claude --allow-native
uv run python evals/records/records.py grade $root --runtime claude
```

Only `run --allow-native` makes model calls. Each run starts a fresh headless
session that bypasses runtime permission prompts, so keep the root disposable.
Transcripts stay in `results/` under the root. `grade` exits nonzero when any
criterion fails.

One pass per runtime is a single sample. Repeat runs in fresh roots before you
treat a result as stable.
