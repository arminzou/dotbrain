# Repository rules

Apply the rules relevant to your change. Reviewers name the rule when reporting a violation.
[AGENTS.md](AGENTS.md) routes agents to guidance; [CONTRIBUTING.md](CONTRIBUTING.md) covers setup and pull requests.

## Code conventions and structure

| Rule | How to apply |
| --- | --- |
| Follow established formatting, naming, and language conventions. | Use [pyproject.toml](pyproject.toml) and nearby code for Python conventions; no formatter or linter is configured. Correct demonstrated defects within scope rather than copying them for consistency. |
| Respect established boundaries between components. | Review responsibilities and dependencies against [the architecture](docs/architecture.md) and the concrete boundaries below. Correct boundary defects within scope without adding unnecessary layers or an unrelated redesign. |
| Keep `paths.py` free of filesystem mutation. | [paths.py](src/dotbrain/paths.py) imports no other `dotbrain` module and performs no writes; other modules depend into it, never the reverse. |
| Keep CLI logic in workflows and the concept modules. | [cli.py](src/dotbrain/cli.py) only parses and renders; limit new behavior there to Typer options and output formatting. |
| Access packaged resources only through `resource_loader.py`. | No other module reads `dotbrain.resources` via `importlib.resources` or file paths; use [the resource accessor](src/dotbrain/resource_loader.py). |
| Register CLI commands on the Typer app. | The package entry point in [pyproject.toml](pyproject.toml) is `dotbrain.cli:app`. Docs and scripts invoke `dotbrain`; `python -m dotbrain` is not wired. |
| Reuse established patterns and add complexity only for a concrete benefit in the current change. | Extract helpers for reuse, complex boundaries, or clearer callers; keep simple single-use expressions inline. Correct defective patterns within scope. Avoid speculative hardening while retaining required security, failure handling, and data protections. |
| Make code express its intent; reserve comments for information the code cannot convey. | Prefer clear names and structure over comments that narrate behavior or explain confusing code. Remove redundant and stale comments and commented-out code. Preserve required legal notices, public API contracts, and verified external constraints or rationale. Keep refactoring within scope. |
| Fix the underlying cause and remove recurring failure paths where practical. | Trace the failure before changing code. Prefer correcting the owning logic, simplifying the design, or making invalid states impossible over adding workarounds. Keep changes within scope; explain necessary workarounds and their limits. |
| Complete the requested change and preserve unrelated work. | Review affected callers, configuration, tests, and the full diff for missing updates. Update or remove affected documentation, examples, comments, and agent guidance so they describe the resulting behavior and no longer prescribe obsolete workarounds. Preserve unrelated edits and avoid unrelated cleanup. |

## Subprocesses

| Rule | How to apply |
| --- | --- |
| Modules that run `bd` or `git` take an injected `run` callable shaped like `subprocess.run`. | New subprocess calls go through the injected `run`; tests that assert on commands pass a fake runner and check the recorded argv. |
| Minimize Git calls in home sync and session hooks. | Each call costs about 0.1 s on Windows. A new `git` call in `home_sync.py` or `hooks.py` asks for something no existing call already returns, such as the branch, upstream, conflicts or changes from `git status --porcelain=v2 --branch`, or the PR says why it must. |

## Input, security, and failure handling

| Rule | How to apply |
| --- | --- |
| Validate untrusted input at its owning boundary and rely on those guarantees internally. | Verify boundary validation and invalid-input cases before relying on its guarantees downstream. Avoid repeating checks for guarantees the boundary actually establishes. |
| Preserve required security checks and protections against data loss. | Review authorization, persistence, and destructive filesystem actions; exercise relevant negative or integration cases to confirm protections still work after the change. |
| Preserve useful failure information and handle errors at the responsible layer. | Propagate errors with useful context; recover or report at the layer that owns that responsibility. Avoid catches that obscure the cause, and exercise failure paths to confirm failures cannot silently appear successful. |
| Keep the tool checkout and the data root (`$DOTBRAIN_HOME`) separate. | Data-root paths come from `paths.resolve_dotbrain_home()`; no code writes Brainspace data into the checkout. |

## Verification

| Rule | How to apply |
| --- | --- |
| Encode requirements in automated checks when violations can be detected reliably. | Use existing types, API boundaries, static analysis, or tests. Verify that the check rejects a representative violation and accepts valid cases. Make failures explain the violated requirement and expected correction. Keep judgment-based decisions in written guidance. |
| Verify the change with evidence appropriate to its behavior. | Run affected tests with `uv run pytest tests/<file>.py`; use [the docs editing guide](docs/AGENTS.md) for site checks. Exercise integrations and interfaces when the claim depends on them. For runtime loading claims, verify discovery or invocation in the affected runtime; delivered resource files alone are insufficient. Distinguish pre-existing failures and state what remains unverified. |
| Prevent demonstrated regressions with targeted checks where practical. | For a behavior fix, reproduce the failure and show the check rejects it and accepts valid behavior, or explain the limitation. Prefer extending existing tests or checks over introducing a framework or brittle wording assertions. |
| Preserve meaningful validation instead of weakening checks merely to pass. | Review tests, suppressions, exclusions, and CI changes. Investigate suppressions before adding or retaining them; fix the underlying issue when the check identifies a real defect. Update expectations when intended behavior changes; justify exceptions narrowly and preserve checks that detect incorrect behavior. |
| Tests use `tmp_path` and never touch a real `$HOME` or the live data root. | New tests set paths under `tmp_path`; nothing reads `~` or `~/dotbrain`. |
| Verify skill behavior through agent evaluations. | The Python suite tests the CLI and plugin delivery: skill tests parse, resolve, or compare packaged files, never assert that a phrase appears in a prompt. Behavioral claims need agent evaluation evidence from [the eval suite](evals/README.md). |
| Add eval cases only for uncovered core capabilities. | A new case names the capability it covers in [the suite README](evals/README.md), with criteria a wrong answer fails. A known-good record passes each assertion and a known-wrong record fails it. Do not add a scenario listed as not ported unless the PR explains what changed. |
| Keep tests safe to run in parallel. | The suite runs under `pytest -n auto`. A test touches only its own `tmp_path`, binds port 0 rather than a fixed port, and changes environment variables or the working directory only through `monkeypatch`. |
| Build shared Git fixtures once per session and copy them for each test. | A fixture or helper used by many tests creates initialized repositories with `tmp_path_factory` and `shutil.copytree`, not with `git init`, `commit` or `push` per test. |
| Tests never need Beads or another external tool installed. | Inject fake runners for external integrations; [tests/conftest.py](tests/conftest.py) hides `bd`, `hermes`, and `pi` and rejects launches of them. Real Git is used by isolated fixtures. |
| Run the full Python suite before pushing or submitting code changes for review. | Run `uv run pytest`; [CI](.github/workflows/ci.yml) must pass on Linux, macOS, and Windows. When several agents share a branch, only the integrating agent runs the full suite; contributors run affected tests. No two full suites run at once. |

## Source hygiene

| Rule | How to apply |
| --- | --- |
| Keep secrets and unintended local state out of tracked source. | Use established configuration and secret mechanisms; inspect the diff and ignore rules. This public tool must work in an ordinary clone without a Brainspace. Include no personal Brainspaces, execution stores, runtime wiring, credentials, private tracker or decision identifiers, or private incident details in source, tests, docs, commits, or PR text. Packaged templates and sanitized examples are intentional source. |
| Gitignore external symlinks and generated runtime resources. | Never track symlinks whose targets are outside the containing repository, or generated runtime resources under `.claude/` and `.codex/`. Confirm `git ls-files` shows no such symlink or generated resource. |

## Skills

| Rule | How to apply |
| --- | --- |
| Keep skills model-invocable unless unasked invocation does unwanted work outside the normal workflow. | Mark those exceptions manual-only in both runtimes, such as a retrospective or other work reserved for explicit invocation. A manual-only skill sets `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in `agents/openai.yaml`; the docs' list of skills that never start on their own names exactly those skills. |

## Documentation

| Rule | How to apply |
| --- | --- |
| `AGENTS.md` is canonical; `CLAUDE.md` is a symlink to it. | `CLAUDE.md` is a symlink, not a separate file. |
| Follow the public documentation guide. | [docs/AGENTS.md](docs/AGENTS.md) owns generated CLI references, configuration examples, English/Chinese pages, site builds, and Mermaid previews in both themes. Check regeneration leaves no further CLI reference diff; state both theme previews in the PR for diagram changes. |

## Commits and PRs

| Rule | How to apply |
| --- | --- |
| Use Conventional Commit messages, as in `fix(cli): explain invalid project selection`. | Each commit subject matches `type(scope): summary`, with the scope optional and `!` marking a breaking change. |
| Explain the problem, resulting behavior, and verification in PRs. | Include before/after screenshots for visual changes. Call out command syntax or JSON output changes with migration steps. |
