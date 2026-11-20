# Selective records and continuation

This eval checks the workflow-independent core with a stock skill workflow.
It runs pstack, with no adapter, in a small task-list repository over two cold
sessions. Each case starts with an unrelated user note and an open, operator-owned
review task. They must survive unchanged.

| Case | First session | Fresh session and expected outcome |
| --- | --- | --- |
| `routine` | Reverse pending-task order, verify, and commit | Explain the actual order from current code; no new Brain records or tasks |
| `experiment` | Probe a proposed streaming JSON write's behavior on serialization failure | Assess safety with evidence and limits; production code unchanged, no need to preserve every probe |
| `continuation` | Store optional due dates and leave the rest of the feature unfinished | Finish overdue ordering and filtering without losing legacy tasks, agreed scope, or necessary work state |
| `retirement` | Remove obsolete daily-digest docs and design; repair pointers | Describe current commands without reviving the removed feature; retain unrelated notes and work |

The session-start convention and the normal discoverable core skills supply
Dotbrain guidance. The workflow owns execution. No case requires a Brain write
merely to prove that capture happened.

## Artifact checks and independent review

The grader runs a caller-visible probe rather than trusting the agent's tests:
task ordering for `routine`, date storage and overdue behavior for `continuation`,
and unchanged production code for `experiment` and `retirement`. Listing probes
use the existing `ID:` prefix and permit additional display details.
It checks that sessions exited successfully, user notes and existing work remain,
and neither session retrieved prior transcripts. Retirement also checks removal
and local Markdown pointers. Routine checks that no new durable records appeared.
Temporary repository artifacts are not rejected merely for existing.

Judgment about utility requires a separate human or evaluating agent that did not
execute the task. Inspect both session traces, actual code and Brain diffs, and
the Beads state and history. Do not grade from the final narrative alone:

| Review criterion | Passes when |
| --- | --- |
| `selective_capture` | Durable additions have a continuing purpose and do not duplicate adequate sources; disposable artifacts are not promoted or left as current guidance without need |
| `useful_continuation` | s2 reaches the correct answer or next action from surviving sources, without lost constraints, needless repetition of expensive investigation, or revival of obsolete work |
| `scope_preserved` | Changes respect the task, user material, acceptance, ownership, and verification gaps; s1's partial-work limit is respected in `continuation` |

For the experiment, check the serialization-failure observation and distinguish
it from crash safety or concurrent-write guarantees that the probe did not test.
A concise conclusion can be retained without its fixture. Leaving it in the
existing source is also valid when that adequately supports later understanding.
For continuation, inspect the s1 handoff before s2 runs: it must identify the
candidate, actual completed work, remaining criteria, evidence or gaps, and next
action in Beads as needed. A successful `bd ready` call alone proves none of this.

Save the independent assessment outside the evaluated checkout and pass it to
`grade --review`. Each criterion needs a Boolean `passed` and an `evidence`
string naming concrete trace events, paths, revisions, or work fields. Missing
assessments fail. This file records review judgments; the grader cannot establish
their truth or independence from JSON alone.

```json
{
  "selective_capture": {"passed": false, "evidence": ""},
  "useful_continuation": {"passed": false, "evidence": ""},
  "scope_preserved": {"passed": false, "evidence": ""}
}
```

## Model-free calibration

```sh
cd evals/records && uv run python -B -m unittest -v test_records
```

Synthetic good and wrong artifacts calibrate the probes, preservation checks,
cleanup checks, and review requirements. They do not establish native agent
behavior or validate a reviewer's semantic judgments.

## Native runs

Use a new root outside every wired checkout, one per case and runtime. `prepare` clones the
local pstack checkout into the root's private home and snapshots the selected core
plugin, convention, and Markdown scaffolds, so nothing is downloaded:

```powershell
$root = Join-Path $env:USERPROFILE 'qualifications/records-claude'
uv run python evals/records/records.py prepare $root --pstack C:/src/pstack --case routine
```

Before the first session, sign in inside the root's isolated runtime home:
`home/claude` (`CLAUDE_CONFIG_DIR`) or `home/codex` (`CODEX_HOME`). For Codex,
also install the snapshotted `ROOT/plugin` into `home/codex` and trust its hooks. Claude
receives that snapshot through `--plugin-dir`. To reuse a signed-in
home, pass `--runtime-home`; clear its earlier sessions and Codex memories between roots. On Windows, set
`CLAUDE_CODE_GIT_BASH_PATH` for headless Claude.

```powershell
uv run python evals/records/records.py run $root --runtime claude --session s1 --executable claude --allow-native
uv run python evals/records/records.py run $root --runtime claude --session s2 --executable claude --allow-native
uv run python evals/records/records.py grade $root --runtime claude --review C:/tmp/routine-review.json
```

Only `run --allow-native` makes model calls. Each run starts a fresh headless
session that bypasses runtime permission prompts, so keep the root disposable.
Transcripts, exit status, elapsed time, candidate revision, and per-session Beads
lists stay in `results/` under the root. Inspect full issue details and comments
when needed; list snapshots alone are not complete execution evidence.
`grade` exits nonzero when any artifact or review criterion fails.

## Compare guidance

Use this harness and the same CLI for both arms. Pass `prepare --guidance-from
C:/src/dotbrain-before` for the baseline source checkout, and the candidate checkout
for the other arm. Both sources must use the five-skill core contract. This changes
the guidance snapshot while holding fixture construction and project identity constant;
the old checkout need not contain the new scenarios.
Keep the scenario, pstack revision, runtime/model, permissions, and available tools
the same; isolate previous sessions and memories. Do not give the executing agent
the grader or expected answer.

Compare actual Brain and work-record additions, duplicates, temporary artifacts
left in normal retrieval, repeated investigation, read/tool calls, elapsed time,
and token usage where the runtime reports it. Judge these alongside task success
and preserved continuity, not as a contest to minimize document counts.
Blind the independent reviewer to baseline/candidate labels where practical.
One pair is a sample; repeat in fresh roots before claiming a stable improvement.
