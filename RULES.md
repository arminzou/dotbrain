# Repository rules

Apply the rules relevant to the change. Reviewers name the rule when reporting a violation.
[AGENTS.md](AGENTS.md) routes agents to guidance; [CONTRIBUTING.md](CONTRIBUTING.md) covers setup and pull requests.

## Architecture

| Rule | What to check |
| --- | --- |
| Keep `paths.py` free of filesystem mutation; other modules depend into it, never the reverse. | `paths.py` imports no other `dotbrain` module and performs no writes. |
| Keep CLI logic in `workflows` and the concept modules; `cli.py` only parses and renders. | New behavior in `cli.py` is limited to Typer options and output formatting. |
| Access packaged resources only through `resource_loader.py`. | No other module reads `dotbrain.resources` via `importlib.resources` or file paths. |
| The package entry point is `dotbrain.cli:app` (Typer); `python -m dotbrain` is not wired. | New commands register on `app`; docs and scripts invoke `dotbrain`, not `python -m dotbrain`. |

## Subprocesses

| Rule | What to check |
| --- | --- |
| Modules that run `bd` or `git` take an injected `run` callable shaped like `subprocess.run`. | New subprocess calls go through the injected `run`; tests that assert on commands pass a fake runner and check the recorded argv. |
| Code that runs at every session (home sync and the hooks) gets what it needs from as few `git` calls as possible; each costs about 0.1 s on Windows. | A new `git` call in `home_sync.py` or `hooks.py` asks for something no existing call already returns, such as the branch, upstream, conflicts or changes from `git status --porcelain=v2 --branch`, or the PR says why it must. |

## User data and filesystem changes

| Rule | What to check |
| --- | --- |
| Keep the tool checkout and the data root (`$DOTBRAIN_HOME`) separate. | Data-root paths come from `paths.resolve_dotbrain_home()`; no code writes Brainspace data into the checkout. |
| Gitignore symlinks whose targets are outside the containing repository, and generated runtime resources under `.claude/` and `.codex/`; never track them. | `git ls-files` shows no such symlink or generated resource. |

## Verification

| Rule | What to check |
| --- | --- |
| Tests use `tmp_path` and never touch a real `$HOME` or the live data root. | New tests set paths under `tmp_path`; nothing reads `~` or `~/dotbrain`. |
| Add a regression test for a behavior fix where practical. | The fix PR includes a test that fails without the fix, or explains why not. |
| The Python suite tests the CLI and plugin delivery, not skill wording; skill behavior needs agent evaluation evidence from the [eval suite](evals/README.md). | Skill tests parse, resolve, or compare packaged files; none asserts that a phrase appears in a skill or agent prompt. |
| The eval suite covers dotbrain's core capabilities, not every scenario. Add a case only for a core boundary no existing case covers, with criteria a wrong answer fails. | A new case names the capability it covers in the suite README; a known-good record passes each of its assertions and a known-wrong record fails it; it is not a case the README lists as not ported, unless the PR says what changed. |
| Tests are safe to run in parallel: the suite runs under `pytest -n auto`. | A test touches only its own `tmp_path`, binds port 0 rather than a fixed port, and changes environment variables or the working directory only through `monkeypatch`. |
| Fixtures that need initialized Git repositories build them once per session and copy them into each test. | A fixture or helper used by many tests creates its repositories with `tmp_path_factory` and `shutil.copytree`, not with `git init`, `commit` or `push` per test. |
| Tests never need Beads or another external tool installed. | Code that runs `bd` gets a fake runner; the suite fails any test that launches real `bd`. |
| Run `uv run pytest` before pushing or submitting code changes for review; CI must pass on Linux, macOS, and Windows. When several agents work on one branch, the integrating agent runs the full suite and contributors run affected tests (`uv run pytest tests/<file>.py`). | PR checks are green on all three platforms; no two full suites run at once. |

## Skills

| Rule | What to check |
| --- | --- |
| A skill is model-invocable unless the normal workflow never needs it and running it unasked does unwanted work, such as building a site, writing a retrospective, starting a learning path or reviewing architecture. Mark such a skill manual-only in both runtimes. | A manual-only skill sets `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in `agents/openai.yaml`; the docs' list of skills that never start on their own names exactly those skills. |

## Public/private boundary

| Rule | What to check |
| --- | --- |
| This repository is the public tool and never holds anyone's project data; do not assume a `.brain/` is present. | Code, tests, and docs work in an ordinary clone with no Brainspace wired. |
| Contributions stand alone without the maintainer's private context. | No personal Brainspaces, execution stores, runtime wiring, credentials, or private tracker/decision identifiers in the diff, commits, or PR text. |

## Documentation

| Rule | What to check |
| --- | --- |
| `AGENTS.md` is canonical; `CLAUDE.md` is a symlink to it. | `CLAUDE.md` is a symlink, not a separate file. |
| Regenerate the CLI reference after changing CLI help. | `uv run python -m dotbrain._cli_reference` produces no diff. |
| Check Mermaid diagrams visually in light and dark themes. | The PR states both themes were previewed; a docs build alone is not enough. |

## Commits and PRs

| Rule | What to check |
| --- | --- |
| Use Conventional Commit messages, as in `fix(cli): explain invalid project selection`. | Each commit subject matches `type(scope): summary`, with the scope optional and `!` marking a breaking change. |
| Explain the problem, resulting behavior, and verification; call out command syntax or JSON output changes with migration steps. | The PR body covers each, with screenshots for visual changes. |
