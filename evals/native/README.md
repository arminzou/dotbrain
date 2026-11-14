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

To include supported CLI attachment in that external check, also set
`NATIVE_FIXTURE_DOTBRAIN` to a candidate CLI executable and
`NATIVE_FIXTURE_PSTACK` to its usable pstack source. The check verifies real links
and preserved backend identity/records. Use the final integrated candidate for
mode-delivery evidence; an older CLI attachment smoke proves only attachment.

On Windows, setting `NATIVE_FIXTURE_PROCESS_CHECK=1` also exercises the process
controls against a temporary Python sleeper, with no agent runtime or model call.

## Prepare and deliver

Use a distinct new root for each runtime. Keep the controller's existing global
session ledger and earlier initiative evidence; creating a fixture grants no new
allowance. Existing roots and exports are never overwritten.

```powershell
python evals/native/journey.py prepare evals/results/catalog-codex --candidate C:/candidate --pstack C:/pstack --bd C:/tools/bd.exe
python evals/native/journey.py wire evals/results/catalog-codex --executable C:/candidate-cli/dotbrain.exe
python evals/native/journey.py plan evals/results/catalog-codex --runtime codex --phase first
```

`prepare` initializes a Git data root and source Brainspace at
`data/brainspaces/catalog/`, with an actual embedded Beads backend, contract
prerequisite, dependent API/UI tasks, integration task, private decision and
random sentinel. The adopter Git repository starts without `.brain` or `.beads`
entries. Its project declaration records embedded mode and pstack opt-in without
an obsolete private skill selection. Candidate/pstack revisions and Beads version
are recorded. It uses neither `items.json` nor a fake tracker. The `bd` proxy delegates
to the specified binary and retains actual argv, actors, output and exit status.

`wire` is the supported delivery prerequisite. It invokes the supplied candidate
CLI's `wire --home ROOT/data --repo ROOT/workspace --project catalog --json`, with
candidate `src` on `PYTHONPATH`, bytecode writes disabled, and all home/backend/Git
destinations inside the fixture. It captures the actual CLI result, candidate
revision, repository-link targets and unchanged seeded graph. The CLI owns link
and resource creation; no delivery links are hand-built. Failed delivery remains
an explicit prerequisite and retains its receipt; native launch refuses it.
An integrated candidate with pstack support is required before mode qualification.
Deliver hooks/resources into each fresh runtime home as needed; inventory alone
does not qualify invocation. Candidate and pstack source homes are never mutation
targets.

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
--include-partial-messages` or `codex exec --json --full-auto --add-dir ROOT -`, with task text
on stdin. No provider sanitizer runs.

The fixed Codex additional directory grants the isolated Brainspace/worktrees
write access while keeping its sandbox enabled. For vetted fixture hooks, the
controller can explicitly add `--trust-fixture-hooks`; its native argv records
the resulting hook-trust option. This never enables a full sandbox bypass.

The first task records a verified discovery and unresolved hypothesis, exercises
competing claims and delegated candidates, retains a failing check, then waits
for deliberate controller interruption. Choose the first timeout to leave time
for that work. Timeout or Ctrl+C terminates and reaps the native parent; its PID,
exit status and interruption are recorded. This never establishes that delegated
writers stopped. Child lifecycle evidence is checked separately and uncertain
authority remains held. A cold second task receives only the fixed continuation
request and task IDs, retrieves durable records and records the operator boundary.

The coordinator claims API/UI tasks under its own Beads actor. Each delegated
native assignment names its task ID and a separate worker label (`workerActor`).
Each worker returns this qualification JSON alongside its normal result, and
the coordinator records it in that task's Beads comments using the actual short
branch name and candidate revision:

```json
{"qualification":{"taskId":"sample-api","workerActor":"api-writer","branch":"feature/api","revision":"0123456789abcdef0123456789abcdef01234567"}}
```

The verifier keeps coordinator claims distinct from actual native worker
identities. It correlates each worker's returned task/label/branch/revision with
the assignment and coordinator-recorded comment, then checks branch snapshots,
Git objects, implementations and ancestry of the checked integration revision.
A coordinator mention, a bare completed-worker status, or an unrelated worker
earns no candidate-return credit.

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
{"decision":"authorize-takeover","actor":"operator","observedOwner":"coordinator-old"}
```

This file is scenario control for the already-authorized operator branch; it
adds no human UAT or product approval gate. The lead/test driver can supply its
explicit synthetic resolution after checking the affected fixture writers.
It never substitutes for the independent stop receipt or native child lifecycle
evidence. Without all three, integration refuses to launch. The controller
rechecks stopped process IDs immediately before integration. A changed claim
still requires native inspection and its ownership guard.

Confirmed recovery must retain successful `bd update --if-assignee OLD
--assignee NEW --actor NEW --json` receipts for both coordinator-owned API/UI
claims, matching the observed old owner and resulting new owner. Do not combine
the guard with `--claim` or `--force`. Under the new coordinator, close API/UI
work with JSON results, query `bd ready --json` after both closures, then claim
and eventually close integration. The gate checks this order, actual returned
owners/statuses and final state; missing/failed/changed guards, open prerequisites
or forced closures cannot pass.

```powershell
python evals/native/journey.py plan evals/results/catalog-codex --runtime codex --phase integration
# Arrange this fresh home's resources and subscription auth.
python evals/native/journey.py run evals/results/catalog-codex --runtime codex --phase integration --executable C:/tools/codex.exe --allow-native
```

Attempts reserve allowance before launch and retain failures. Defaults stop
after three consecutive nonzero exits and twelve sessions per fixture. An
explicitly authorized uncapped run adds `--uncapped` to each native call; every
receipt records that override and the unchanged defaults, keeping all earlier
attempts and exhausted prior initiative allowances. The controller applies its
current approved policy across fixtures. Deliberate interruption remains a
nonzero exit rather than silently reset. The native process environment directs home,
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
successful `cat`, `Get-Content` or `type` command with matching output. Cold
continuation permits explicit file/editor targets in the workspace, owning Brain
and vetted resource sources (including the integration cache), plus bounded graph
and read-only Git queries. Embedded backend probes use `bd --readonly ready
--json`; server probes may use `bd dolt test` or `bd --readonly dolt test`.
Candidate doctor queries keep home/repo selectors bound to the fixture.
Backend routing overrides and actor-free mutations remain refused. Native
Python entrypoints use candidate `src` with bytecode disabled. Skill-loading
credit is limited to the vetted core and selected mode; unknown indirect
loaders cannot establish cold access.
Recursive, glob, indirect, unestablished or delegated reads cannot qualify;
unfinished/unsupported native tool activity also holds the gate. This is an
allowed-read boundary, not a blacklist of transcript filenames.
Claude worker credit needs linked child activity and a successful synchronous
candidate return; Codex needs native spawn/completion and the candidate message
linked to that actual worker identity. Unsupported CLI telemetry is held rather
than inferred from a final narrative. Completion is distinct from
OS process termination; the fixture deliberately exercises the operator path
for uncertain takeover.

Check credit requires a simple interpreter invocation of the actual fixture
`check.py`, its native exit status, and the script's JSON result carrying its
unchanged script digest and checked commit. Reading, echoing or mentioning the
script earns no execution credit. Passing integration must precede a separate
native close call, corroborate Beads closure, preserve a clean final checkout,
and include both actual API/UI candidates. Cold-continuation access checks use
Windows path identity, including casing, relative traversal and filesystem
aliases; even partial reads of prior controller artifacts invalidate continuation.
The private sentinel is checked in tracked files and the retained candidate
commit. Broader discovery, opt-out and preservation scenarios remain separate
qualification work.

This gate checks config/discovery retrieval and reuse. Actual planted-decision
retrieval, late-worker-result races and privacy in ignored delivered resources
remain separate qualification checks; the seventeen criteria do not establish
all continuity, recovery or public-delivery outcomes.

`export` preserves raw files, hashes the raw/export pairs, redacts recognized
credential fields (including encoded JSON), bearer credentials, known secret
assignments, private sentinels and fixture/source paths without depth truncation.
Actor identities, read contents and usage telemetry survive. It never traverses
runtime homes or copies auth files. Review exports before publication: arbitrary
unknown secret formats are not proven absent. Export generation proves redaction
behavior; it does not upgrade native outcomes or renew exhausted allowances.
