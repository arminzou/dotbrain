# Native catalog journey

This fixture qualifies connected project knowledge and a real Beads graph through
contract, API/UI delegation, failed verification, interruption, cold recovery,
uncertain ownership, and integration. It runs native CLIs directly and retains
JSONL privately. It does not change the held Promptfoo providers or their records.

## Model-free checks

```powershell
python -m unittest discover -s evals/native -v
node --test --test-concurrency=1 evals/assertions/evidence.test.cjs
```

The default tests use synthetic native records and injected boundaries. Every
assertion has a passing record and a representative failing canary for both
runtime formats. This calibrates the measurement, not agent behavior.

The external backend check is opt-in and uses only a newly created fixture:

```powershell
$env:NATIVE_FIXTURE_BD = (Get-Command bd).Source
python -m unittest discover -s evals/native -v
Remove-Item Env:NATIVE_FIXTURE_BD
```

It retains its embedded Dolt backend and receipts under `evals/results/`. It
checks actual dependency readiness, exclusive actor claims and a failed product
check. It makes no model calls and accesses no authentication files.

On Windows, setting `NATIVE_FIXTURE_PROCESS_CHECK=1` also exercises the process
controls against a temporary Python sleeper, with no agent runtime or model call.

## Prepare and deliver

Use a distinct new root for each runtime. Keep the controller's existing global
session ledger and earlier initiative evidence; creating a fixture grants no new
allowance. Existing roots and exports are never overwritten.

```powershell
python evals/native/journey.py prepare evals/results/catalog-codex --candidate C:/candidate --pstack C:/pstack --bd C:/tools/bd.exe
python evals/native/journey.py plan evals/results/catalog-codex --runtime codex --phase first
```

`prepare` creates an actual isolated embedded Beads backend, contract prerequisite,
dependent API/UI tasks, integration task, Git repository, private decision and
random private sentinel. Candidate and pstack revisions and Beads version are
recorded. It uses neither `items.json` nor a fake tracker. The `bd` proxy delegates
to the specified binary and retains actual argv, actors, output and exit status.

Delivery is a separate prerequisite: use the integrated candidate's supported
wiring/delivery route with the fixture's isolated environment from `plan` and
workspace. Preserve its real backend and private decision. The project declares
`pstack.enabled: true` and the supplied `pstack.source`. Deliver resources and
hooks into each fresh runtime home as needed; inventory alone does not qualify
discovery or invocation. Neither candidate checkout nor pstack checkout is a
mutation target of the fixture.

`plan` returns the exact next home/environment and fixed task without reserving a
session. The controller arranges subscription authentication in that home and
configures the runtime's permitted fixture tools independently. No credential is
read, copied or returned by this harness. The environment excludes inherited API
keys, backend routing and Git overrides; there is no API-billing fallback.
Retain settings in the isolated homes for private inspection. Native attempts
record the CLI version, argv and settings hashes without reading auth files.

## Native phases

Only `run --allow-native` makes model calls. Use a direct native executable path
on Windows. Each invocation gets a new home and session; resume/continue switches
and transcript injection are absent from the command interface.

```powershell
python evals/native/journey.py run evals/results/catalog-codex --runtime codex --phase first --executable C:/tools/codex.exe --allow-native --timeout-seconds 900
python evals/native/journey.py plan evals/results/catalog-codex --runtime codex --phase continue
# Arrange subscription auth and delivered resources in the new home.
python evals/native/journey.py run evals/results/catalog-codex --runtime codex --phase continue --executable C:/tools/codex.exe --allow-native
```

For Claude, use a separate prepared root, `--runtime claude`, and its direct
executable. Calls use `claude -p --verbose --output-format stream-json
--include-partial-messages` or `codex exec --json --full-auto -`, with task text
on stdin. No provider sanitizer runs.

The first task records a verified discovery and unresolved hypothesis, exercises
competing claims and delegated candidates, retains a failing check, then waits
for deliberate controller interruption. Choose the first timeout to leave time
for that work. Timeout or Ctrl+C terminates and reaps the native parent; its PID,
exit status and interruption are recorded. This never establishes that delegated
writers stopped. Child lifecycle evidence is checked separately and uncertain
authority remains held. A cold second task receives only the fixed continuation
request and task IDs, retrieves durable records and records the operator boundary.

To exercise confirmed takeover, the test driver first uses the captured process
identities to stop affected fixture writers:

```powershell
python evals/native/journey.py stop-writers evals/results/catalog-codex
```

The controller records the launched parent's PID, working directory and process
creation time, captures its descendant tree before interruption, and waits for
parent exit. `stop-writers` rechecks each descendant's PID/creation time and
fixture-path command marker before termination, then independently queries the
OS again. Missing scope, changed/reused PIDs or new descendants retain the hold;
unrelated processes are never stopped. The absolute fixture wait script gives
the intentional sleeper and its shell an inspectable fixture-path marker.
Commands are bounded Windows CIM queries and guarded `Stop-Process` calls.

After inspecting actual writer records, the test driver supplies the isolated
scenario resolution in
`private/operator-decision.json` under that fixture root, using the actually
observed owner:

```json
{"decision":"authorize-takeover","actor":"operator","observedOwner":"api-writer"}
```

This file is scenario control for the already-authorized operator branch; it
adds no human UAT or product approval gate. The lead/test driver can supply its
explicit synthetic resolution after checking the affected fixture writers.
It never substitutes for the independent stop receipt or native child lifecycle
evidence. Without all three, integration refuses to launch. The controller
rechecks stopped process IDs immediately before integration. A changed claim
still requires native inspection and its ownership guard.

```powershell
python evals/native/journey.py plan evals/results/catalog-codex --runtime codex --phase integration
# Arrange this fresh home's resources and subscription auth.
python evals/native/journey.py run evals/results/catalog-codex --runtime codex --phase integration --executable C:/tools/codex.exe --allow-native
```

Attempts reserve allowance before launch, retain failures, stop after three
consecutive nonzero exits, and cap each fixture at twelve sessions. The controller
must also enforce the approved total across fixtures, checkpoint failure/no-progress
caps, and the run's deadline. Deliberate interruption is retained as a nonzero
exit rather than silently reset. The native process environment directs home,
temporary files, Git configuration and backend writes into the fixture; this is
not an operating-system security sandbox. Use the runtime's own permissions to
restrict additional writes to the fixture.

## Inspect and qualify

```powershell
python evals/native/journey.py inspect evals/results/catalog-codex
python evals/native/verify.py evals/results/catalog-codex --runtime codex
python evals/native/journey.py export evals/results/catalog-codex
```

Inspect the complete private native JSONL, stderr, fixed inputs, tracker receipts,
before/after graph and knowledge snapshots, settings and actual candidate Git
objects. `verify` needs an adjacent first/continue/integration sequence. Missing,
unsupported or incomplete evidence cannot qualify. It checks seventeen criteria:
distinct sessions, cold input, durable discovery, corroborated reads, recovered
knowledge used in a durable continuation record, real
dependencies, prerequisite closure, competing claims, failed-check hold,
candidate object, worker lifecycle, interruption, uncertain-owner hold, confirmed
writer stop,
integration verification, private boundary, and retained limits.

Read credit requires native Claude Read records with contents or a simple
successful `cat`, `Get-Content` or `type` command with matching output. Complex
shell scripts do not establish a read automatically. Claude worker credit needs
linked child activity and a successful synchronous result; Codex needs native
spawn and completed/shutdown agent-state records. Unsupported CLI telemetry is
held rather than inferred from a final narrative. Completion is distinct from
OS process termination; the fixture deliberately exercises the operator path
for uncertain takeover.

Integration credit requires a passing native `check.py` call before a separate
native close call, corroborating actual Beads closure and final graph state.
The private sentinel is checked in tracked files and the retained candidate
commit. Broader discovery, opt-out and preservation scenarios remain separate
qualification work.

`export` preserves raw files, hashes the raw/export pairs, redacts recognized
credential fields (including encoded JSON), bearer credentials, known secret
assignments, private sentinels and fixture/source paths without depth truncation.
Actor identities, read contents and usage telemetry survive. It never traverses
runtime homes or copies auth files. Review exports before publication: arbitrary
unknown secret formats are not proven absent. Export generation proves redaction
behavior; it does not upgrade native outcomes or renew exhausted allowances.
