# Shared skill evals

[`promptfooconfig.yaml`](promptfooconfig.yaml) is the entry point for one shared
suite on Claude Code and Codex. It covers dotbrain's core capabilities rather than
every retired case: skill loading, worker and review boundaries, closure on fresh
approval, private IDs out of public PRs, and parallel dispatch. Twelve scenarios are
prepared; live qualification is pending.

## Files

```text
promptfooconfig.yaml       # shared runner configuration
package.json              # pinned local Promptfoo and Claude SDK dependencies
providers/                # built-in Claude Agent SDK / Codex app-server settings
tests/*.yaml              # shared scenarios; per-case `fixture` var holds commits, tracker items, tools
fixtures/                 # fresh workspaces through Promptfoo's beforeEach hook
assertions/               # runtime evidence and case-specific Git/state checks
results/                  # ignored workspaces, logs and reports
legacy/                   # frozen inventory of the retired runner's 32 cases
```

The retired runner's case directories are no longer checked out. Their criteria
live in [`legacy/inventory.json`](legacy/inventory.json); read an original file
with `git show <source-revision>:plugin/evals/<path>`. See
[legacy/migration.md](legacy/migration.md) for the 32-case, 87-grader inventory;
the suite deliberately keeps twelve of them.

Not ported, by decision:

- `explicit-only-not-loaded-close-design`: `close-design` now starts from a
  plain-words request, so its criterion no longer holds.
- `activation-manage-work-graph`, `no-skill-for-unrelated-request`: the first
  repeats `activation-review-gate`; the second nearly always passes.
- `accepted-automatic-failure-mode`, `handoff-stop-scopes`,
  `metadata-preserves-checkpoint-state`, `execution-recovery-boundaries`,
  `automatic-failure-blocks-later-runs`, `unreported-automatic-failure-is-high`:
  their regex graders pass on almost any answer, or other cases cover them.
- `handoff-goal-shortfall-final-review`: repeats `goal-shortfall-blocks-final-review`.
- Not core: `final-review-coverage-and-dispositions`,
  `fix-round-from-stored-assignment`, `parallel-group-promotion`,
  `reviewer-records-review-comment`, `goal-shortfall-blocks-final-review`,
  `handoff-admits-goal-shortfall-within-budget`, `worker-rejects-missing-label`,
  `worker-stores-candidate-report`, and the optional `run-retro` skill's
  `retro-records-new-evidence` and `retro-rerun-changes-nothing`.

Cases by capability:

- **Skill loading:** `activation-review-gate`, `explicit-only-not-loaded-run-retro`.
- **Worker boundaries:** `worker-never-pushes`, `lead-alone-changes-work-graph`.
- **Review independence and verdicts:** `review-gate-blocks-self-review`,
  `review-gate-lead-reviews-worker-change`, `observed-revision-mismatch-held`.
- **Closure on fresh approval:** `closure-on-fresh-approval`, `no-closure-on-stale-approval`.
- **Private IDs out of public PRs:** `public-pr-keeps-private-ids-out`.
- **Parallel dispatch and role routing:** `parallel-reference-before-dispatch`,
  `execution-role-routing`.

## Install and check without models

Requires Node.js 22.22 or later, Git, Codex CLI, and the checkout's locked Python environment.
From the repository root:

```sh
uv sync --locked
cd evals
npm ci
npm run validate
npm test
```

`validate` runs the installed Promptfoo config validator. `test` runs deterministic
assertion calibration, real filesystem/Git/stub checks, and the Promptfoo evaluator
with a synthetic provider. These checks make no model, agent or judge calls.
They do not establish native resource loading, sandboxing or behavior quality.

## Run after live qualification is authorized

Choose and record the Codex CLI version, each runtime's OS, model, reasoning settings, authentication, repeat count
and budget before running. Set `DOTBRAIN_EVAL_LIVE=1`, `EVAL_CLAUDE_MODEL`, and
`EVAL_CODEX_MODEL` in that run's environment. Models have no fallback defaults.
Both runtimes run on the operator's subscriptions. Never put secrets in YAML.

- **Claude:** run `claude setup-token` once and export the token it prints as
  `CLAUDE_CODE_OAUTH_TOKEN` in the run's environment. `providers/claude.yaml` sets
  `apiKeyRequired: false`, so no API key is needed; an `ANTHROPIC_API_KEY` in the
  environment would win over the subscription, so leave it unset.
- **Codex:** sign in once with `codex login` (ChatGPT). For each live run the hook copies
  `auth.json` from `$CODEX_HOME` (default `~/.codex`) into the fixture's Codex home. After
  the run it writes a refreshed copy back, unless the original changed meanwhile, and
  deletes the copy. A run that crashes before cleanup can leave the copy under
  `results/`; delete that run directory. An `OPENAI_API_KEY` or `CODEX_API_KEY` in the
  environment would log in with the key instead, so leave them unset.

The fixture copies no other sign-in files or global skills.

```sh
npx promptfoo eval -c promptfooconfig.yaml --no-cache --no-share --max-concurrency 1 -o results/report.json
```

To run one case, pass its file with `-t tests/<case>.yaml`; add `--filter-providers codex`
or `--filter-providers claude` for one runtime. Filtering providers across the whole suite
fails, because Promptfoo checks every test's provider references before filtering.

This is a normal Promptfoo command. The `beforeEach` hook creates a new root for
each case/provider/repeat. A small prompt function binds its final workspace and
environment to the built-in provider and selects the runtime's packaged role name.
It does not generate the suite configuration. The Python delivery helper calls
Dotbrain's product linking functions to stage public skills in `.agents/skills`
and generated Codex roles in `.codex/agents`; Claude loads a local public plugin.
All links resolve inside the synthetic root. Fixtures are retained under `results/`
including failures; remove individual run directories after inspecting them.

State cases use a local origin and synthetic `bd`/`gh` commands. Agent Git activity
is logged separately from setup/checker reads. These environment boundaries are
**not an OS sandbox**; native Windows/WSL/macOS/Linux behavior still needs live
qualification. On native Windows, Codex has no working sandbox and refuses every command
in a sandboxed mode, so Windows runs use `danger-full-access`: the agent can reach any
path the operator can, and only the fixture's homes, environment and stubs bound it.
Elsewhere, read-only cases use Codex's `read-only` sandbox. Claude's provider inherits process environment variables, so the
live run must use a dedicated environment containing only approved credentials.

## Coverage

These mappings preserve the criteria in the frozen inventory. They record
prepared assertions, not accepted live coverage. Source identity is the case ID
plus grader ID; every test also requires `responseComplete`.

| Source case / grader | Promptfoo assertion |
| --- | --- |
| `activation-review-gate` / `skill-invoked` | `skill-used` in `tests/activation-review-gate.yaml` |
| `explicit-only-not-loaded-run-retro` / `skill-file-not-read` | `noSkillRead` |
| Same case / `skill-not-searched` | `noSkillSearch` |
| Same case / `skill-not-invoked` | `noSkillInvocation` plus built-in `not-skill-used` |
| `worker-never-pushes` / `worker-dispatched` | `workerDispatched` |
| Same case / `nothing-closed-or-merged` | `workerState` |
| Same case / `nothing-pushed` | `workerState` |
| `parallel-reference-before-dispatch` / `reference-read` and supplemental completion-before-dispatch criterion | `parallelOrdering` |
| Same case / `two-writers` (minimum two) | `twoWorkersDispatched` |
| Same case / `serial-fallback` | Retired: both runtimes now isolate parallel workers, so the fallback precondition is gone |
| `execution-role-routing`, `observed-revision-mismatch-held` / every grader | One assertion per grader, named by `metric`; see below |
| `closure-on-fresh-approval`, `no-closure-on-stale-approval`, `review-gate-blocks-self-review`, `review-gate-lead-reviews-worker-change`, `public-pr-keeps-private-ids-out`, `lead-alone-changes-work-graph` / every grader and state rule | One assertion per grader (`metric` is its id) and per state rule (`metric` is `state:<rule>`); see below |

The `noSkill*` checks read the forbidden skill from the test's `skill` var; a
missing or malformed name is `INCONCLUSIVE`.

Custom runtime checks live in `assertions/evidence.cjs`; state checks live in
`assertions/state.cjs`. The built-in skill patterns are globs so they accept both
Claude's namespaced names and Codex's unprefixed names in the staged public bundle.

`workerState` covers every source state rule: `no-push`, `no-merge`, `no-close`,
`committed`, `delivered=CONTRIBUTING.md:make test`, and `branch-unchanged=main`.
The file must exist in a new local branch head; a working-tree edit alone fails.
The local `main` ref must equal its fixture baseline; the active branch may differ.

`parallelState` covers `no-close=demo-4`, `no-close=demo-5`, `no-push`, and
`no-merge`. The original parallel state contract does not require `main` to remain
the active branch.

The two decision exercises give the agent a written scenario and grade its answer;
they need no fixture state. Each source regex keeps its pattern, with inline `(?is)`
flags moved to `RegExp` flags; each `no-dispatch` grader is `noDispatch`, which
fails on any Claude `Agent` call or Codex `spawnAgent` event. Offering `Agent`
without Bash, Write or Edit keeps Codex in its read-only sandbox. A known-good
answer per case must pass every grader and a wrong answer or a dispatch must fail
each one.

The six state cases are generated from the frozen inventory: prompt, turn limit,
graders and state rules, with a fixture transcribed from each source `fixture.sh`.
The fixture's commits may sit on named branches with an author and a `name`; items
and rules refer to revisions as `$main`, `$head` or `$<name>`. The `bd`/`gh` stub
logs each call's actor and any body passed by `--file`, `--body-file` or `-F`, and
answers commands listed in `fixture.responses`. `callsLog` renders those calls as
the retired runner's tab-separated `calls.log`, so a source grader's pattern applies
verbatim; an `absent` pattern needs logged agent activity first. `sourceRule` ports
the retired checker's rules (`no-push`, `no-merge`, `no-close`, `closed`,
`no-approval`, `verdict-recorded`, `committed`, `delivered`, `branch-unchanged`,
`no-private`, `no-graph-write-by`, `no-actorless-graph-write`) and fails every rule
when no bd, gh or top-level Git call was logged. It also counts the attached
`-sclosed` form as a closure, which the retired checker missed. A test without
`Agent` also turns off Codex's `multi_agent`, but Codex 0.163 still offers
`spawn_agent`, so `review-gate-blocks-self-review` runs on Claude only.

### Provider capability exclusions

`SKIPPED_UNSUPPORTED` records are coverage exclusions, never passing assertions.
They live in test `metadata.capabilityExclusions` and are retained in Promptfoo's
JSON report, outside scoring. Provider filters omit the Codex explicit-only and
self-review combinations entirely, so the normal matrix executes twenty-two
combinations per repeat: twelve Claude and ten Codex. An omitted combination has no
result row.

| Provider | Source case / grader | Excluded criterion | Retained scoring |
| --- | --- | --- | --- |
| `openai:codex-app-server` | `explicit-only-not-loaded-run-retro` / `skill-file-not-read`, `skill-not-searched`, `skill-not-invoked` | Strict absence of skill reads/searches/invocation | None; no execution or result row for this combination |
| `openai:codex-app-server` | `review-gate-blocks-self-review` / `no-approval-recorded`, `reports-blocked` | No independent reviewer available to the lead | None; Codex 0.163 still offers `spawn_agent` with `features.multi_agent` off, so the premise cannot be set up |
| `openai:codex-app-server` | `worker-never-pushes` / `worker-dispatched` | Linked child-tool activity | `codexWorkerDispatched` requires a successful lead spawn of `dotbrain-worker` and that child's finished turn; `workerState` remains mandatory |
| `openai:codex-app-server` | `lead-alone-changes-work-graph` / `two-workers-dispatched` | Linked child-tool activity | `twoCodexWorkersDispatched` requires two successful `dotbrain-worker` spawns and two finished child turns; every state rule remains mandatory |
| `openai:codex-app-server` | `parallel-reference-before-dispatch` / `two-writers` | Linked child-tool activity | `twoCodexWorkersDispatched` requires two successful `dotbrain-worker` spawns and two finished child turns; ordering and state checks remain mandatory |

Promptfoo 0.125.0 drops child-thread events from its raw event stream, so Codex
child activity criteria are excluded. Codex 0.163 spawns through raw `collaboration`
function calls rather than collab items: a spawn counts when the lead's
`spawn_agent` call asked for `agent_type: dotbrain-worker` and Codex returned a
task, and each counted child must log a finished turn in the fixture's own Codex
log (`home/.codex/logs_*.sqlite`). Codex shell events cannot prove
absence of indirect skill reads/searches or invocation, so the whole Codex
explicit-only combination is excluded. Scores describe only retained criteria; a
green Codex worker row does not establish named-role coverage or parity. Codex
positive `skill-used` remains a labeled heuristic.

### Evidence rules

Missing/malformed terminal, tool, trace or state evidence fails closed with an
`INCONCLUSIVE` reason. It cannot pass a negative criterion through absence.
Claude ordering uses tool-call IDs and completed trace timestamps. Codex requires
a lead command, completed before the first dispatch, whose output contains the staged
reference's full contents and which reads it by a native `commandActions` read
resolved against its `cwd`. Promptfoo flattens nested arrays in raw events to
`'[...]'`; then the command itself must name the reference. A later failing command
in the same shell call does not undo the read. A path mention without the contents
earns no credit. Claude negatives require native Read/Grep/Glob/Skill records;
unexpected shell or agent calls are inconclusive, except a refused call to a tool
the test did not offer, which never ran.

After the first live pilot, by decision: the parallel case's serial-fallback
grader is retired because both runtimes isolated the workers in worktrees, and the
`fresh-review` and `names-unreviewed-change` regexes are widened to accept the
correct answers that pilot gave (a re-request about the requested boundary;
`BATCH_SIZE` and "since advanced"). After the first rerun, `held` also accepts a
hold decision and the observed-revision mismatch in nearby sentences of one paragraph.
Correct live answers a grader once rejected are kept in `assertions/live-answers.json`,
and calibration keeps them passing. Tool permissions, child tool availability and
runtime sandboxing still require qualification.

Inspect nonzero coverage, individual assertion results, transport/grader errors,
runtime/model versions, traces and retained workspaces. Seeded replay records test
the assertions; they are not live behavior evidence. The initial dependency audit
also reports high-severity transitive advisories in proxy/FTP and optional Azure
authentication paths. No automatic breaking downgrade was applied; review the
current `npm audit` report before live qualification.

Official references: [agent-skills guide](https://www.promptfoo.dev/docs/guides/test-agent-skills/),
[extension hooks](https://www.promptfoo.dev/docs/configuration/reference/#extension-hooks),
[dynamic prompts](https://www.promptfoo.dev/docs/configuration/prompts/#function-with-configuration),
and [Promptfoo's agent skills](https://www.promptfoo.dev/docs/integrations/agent-skill/).
