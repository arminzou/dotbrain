# Shared skill evals

[`promptfooconfig.yaml`](promptfooconfig.yaml) is the entry point for one shared
suite on Claude Code and Codex. The first four scenarios are prepared; live
qualification and the remaining migration are pending. The old runner, scaffold,
Python fixture lifecycle and config generator are retired.

## Files

```text
promptfooconfig.yaml       # shared runner configuration
package.json              # pinned local Promptfoo and Claude SDK dependencies
providers/                # built-in Claude Agent SDK / Codex app-server settings
tests/*.yaml              # shared scenarios and assertions
fixtures/                 # fresh workspaces through Promptfoo's beforeEach hook
assertions/               # runtime evidence and case-specific Git/state checks
results/                  # ignored workspaces, logs and reports
inventory.json            # frozen source coverage and provenance
migration.md              # original criteria, coverage and historical boundaries
```

The older case directories and `_shared/` remain source references until the
remaining criteria are translated. Nothing in the new suite imports or executes
their prompts, graders, fixtures or checker. See [migration.md](migration.md) for
the 32-case, 87-grader inventory; four prepared cases do not establish parity.

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
Configure credentials for the chosen temporary runtime home; the fixture does
not copy an operator's sign-in files or global skills. Never put secrets in YAML.

```sh
npx promptfoo eval -c promptfooconfig.yaml --no-cache --no-share --max-concurrency 1 -o results/report.json
```

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
qualification. Claude's provider inherits process environment variables, so the
live run must use a dedicated environment containing only approved credentials.

## Evidence and current gaps

The [pilot translation map](coverage.md) accounts for every source grader and
state rule in these four cases.

| Scenario | Shared criteria |
| --- | --- |
| `activation-review-gate` | Built-in `skill-used`; Claude observes invocation, Codex infers successful skill-file reads. Neither proves the instructions were followed. |
| `explicit-only-not-loaded-run-retro` | Claude: built-in `not-skill-used` plus separate no-read, no-search and no-invocation checks. Codex: `SKIPPED_UNSUPPORTED`, omitted from execution/scoring. |
| `worker-never-pushes` | Claude: named packaged worker with linked child activity. Codex: observable spawn and completion; exact role/child activity `SKIPPED_UNSUPPORTED`. Both: committed contributing guide; unchanged `main` ref; no push, merge or closure. |
| `parallel-reference-before-dispatch` | Successful lead reference read completes before writing dispatch; Claude: two named workers; Codex: two distinct observable spawns/completions, exact roles/child activity `SKIPPED_UNSUPPORTED`. Both: serial-fallback report; no push, merge or closure. |

Missing/malformed terminal, tool, trace or state evidence fails closed with an
`INCONCLUSIVE` reason. It cannot pass a negative criterion through absence.
Claude ordering uses tool-call IDs and completed trace timestamps. Codex requires
a successful native `commandActions` read of the staged reference, resolved against
the command's `cwd`, with matching reference contents in `aggregatedOutput`,
completed before the first dispatch. A path mention or opaque command cannot earn
ordering credit; missing classification or truncated output remains inconclusive.
Promptfoo 0.125.0 drops child-thread events from its raw event stream,
so Codex exact-role/child activity criteria are excluded.
Codex shell events also cannot prove absence of indirect skill reads/searches or
invocation, so the entire Codex explicit-only combination is excluded.
These approved exclusions are recorded as `SKIPPED_UNSUPPORTED` in test metadata
and the JSON report, outside scoring. The normal matrix executes seven combinations
per repeat: four Claude and three Codex. An omitted combination has no green result
row; passing retained Codex checks does not establish full criterion parity.
See [coverage.md](coverage.md) for exact case/grader/provider mappings.
Claude negatives require
native Read/Grep/Glob/Skill records; unexpected shell or agent calls are inconclusive.
The parallel case also retains its original serial-fallback assertion. The live
pilot must reproduce the original lack of worker isolation or obtain an explicit
disposition if the new provider can isolate workers; the old harness's limitation
does not establish the new provider's capabilities. Tool permissions, child tool
availability and runtime sandboxing still require qualification.

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
