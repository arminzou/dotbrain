# Disposable fixtures

`fixture.py` provides setup, run, assert, and cleanup for the shared synthetic
cases. It uses Python's standard library, Git, Bash, the existing case fixtures,
and the shared state checker. It does not import Promptfoo or an agent SDK, choose
a model, or make model calls. No additional dependency is required.

Each setup allocates a new temporary root, including for identical
case/provider/repeat identities. The returned JSON contains `manifest`,
`workspace`, `home`, `origin`, `fixture_state`, `calls`, `pushes`, `evidence`, and
`env`. All mutable fixture paths are under that root. Setup builds repositories
**at their final location**. Never clone, move, or copy a prepared fixture: Git
remotes, shell profiles, PATH and Trace2 contain absolute bindings. Loading a
manifest from a copied root is rejected. A clone also lacks the ignored fixture
state and is not a qualified workspace.

## Interface

Use Python 3.11 or later. On Windows, explicitly select the Git installation's
`bin/bash.exe`; the default `bash` may be WSL. For example in PowerShell:

```powershell
$shell = (Join-Path $env:ProgramFiles 'Git/bin/bash.exe')
$fixture = python plugin/evals/promptfoo/fixture.py setup activation-review-gate codex --repeat 0 --bash $shell | ConvertFrom-Json
# Resource staging belongs here, within $fixture.root, before run.
python plugin/evals/promptfoo/fixture.py run $fixture.manifest -- $shell --noprofile --norc -c 'bd where; gh pr view 1; git log -1'
python plugin/evals/promptfoo/fixture.py assert $fixture.manifest
python plugin/evals/promptfoo/fixture.py cleanup $fixture.manifest
```

`setup CASE PROVIDER [--repeat N] [--parent TEMP_PARENT] [--bash EXECUTABLE]`
returns the JSON references. Provider is an identity, not an SDK selector.
Non-state cases receive the shared base scaffold, so the pilot can use the same
workspace/evidence interface. Their default state rules cover no push, merge, or
closure; these supplement their transcript graders rather than replace them.

`run [--dry-run] MANIFEST -- COMMAND ...` launches exactly the supplied command
at the final workspace with the isolated environment. `--dry-run` only prints
the launch specification; it does not execute commands, reset logs, or write
state. Use one actual invocation per fixture. Nonzero exits and interrupted
launches cannot pass assertions. Stdout, stderr, argv, and exit status are saved
under `evidence/`. Use absolute executable paths for tools outside Git's tool
directories: the inherited host PATH is deliberately absent. In particular,
the supplied shell resolves `bd` and `gh` only to the fixture stubs.

`assert MANIFEST` runs the canonical case's `checks` and writes
`evidence/assertions.json` before any cleanup. It fails on missing, empty, or
invalid activity logs; setup/probes and checker Git reads never establish agent
activity. The fixture has an independent local origin with a push logging hook;
stubs record all tracker/hosting arguments and bodies, serving only synthetic
responses from `.eval/fixtures/`. A failure leaves the complete root intact.

`cleanup MANIFEST` deletes the validated temporary root only after stored
assertions pass. Export any evidence needed for a report before cleanup.
There is no automatic finally-block cleanup and no force-delete option.

Python callers can import the file with `importlib.util` and use
`setup(case, provider, repeat, parent=..., bash=...)`,
`run(fixture, argv, dry_run=False)`, `assert_fixture(fixture, rules=None)`, and
`cleanup(fixture)`. `load(manifest)` reopens the returned references.
An explicit `rules` list is useful for model-free lifecycle tests; live case
integration must preserve the canonical checks and transcript assertions.

## Built-in provider integration seam

Preallocate one fixture and one built-in-provider configuration per
case/provider/repeat. Set the provider's `working_dir` to the returned final
`workspace`, disable workspace copying (`copy_working_dir: false` where
supported), and give the provider subprocess the returned environment. Run
Promptfoo from an external launcher with that same environment. Keep one
case/provider/repeat in that config; allocate independent roots and configs
before launching concurrent trials. Do not mutate a shared provider from
`beforeEach`. Keep provider config and reports under the returned evidence
directory, outside the workspace.

Promptfoo 0.125.0 source inspection supports this seam: Claude Agent SDK resolves
a static `working_dir`; Codex SDK renders config variables before resolving its
working directory. The lifecycle does not depend on provider cloning, callbacks,
or a custom provider. This is an integration seam, not a live provider test.
The pilot owns provider config materialization, authentication, runtime/resource
delivery, native loading, transcript assertions, and final report export.
The launcher must explicitly supply any later-authorized authentication; setup
never inherits tokens or personal runtime configuration.

Stage resources **after setup**, through the real delivery interface using only
the returned synthetic `DOTBRAIN_HOME`. All symlink/junction targets must exist
inside the temporary root; external and dangling links fail before run/assert.
Run and assert validate links. This does not copy the operator's skills or Brain,
and creating files does not establish native runtime discovery.

The fixture environment is not an OS sandbox or a security boundary against
arbitrary commands. Absolute executable paths can bypass PATH, and processes can
access host files/network unless the pilot adds an independently qualified OS
sandbox. These trials establish final-path bindings and stub resolution for the
tested commands, not native skill loading, model behavior, or universal isolation.

## Model-free checks

```powershell
$env:PROMPTFOO_BASH = (Join-Path $env:ProgramFiles 'Git/bin/bash.exe')
uv run pytest tests/test_promptfoo_fixtures.py
uv run python plugin/evals/_shared/check.py --selftest --bash $env:PROMPTFOO_BASH
uv run pytest
```

On POSIX, the tests select the installed Bash by default. Windows tests skip
the shell trials unless `PROMPTFOO_BASH` is set explicitly. The trials cover
sequential repeats and concurrency across case/provider identities, final
remote/PATH/Trace2 bindings, stub recording, setup/checker activity separation,
invalid or missing logs, failure retention, copy/clone rejection, internal and
external links, dry-run immutability, and cleanup after successful assertions.
