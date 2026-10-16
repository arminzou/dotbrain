# Repository rules

Apply the rules relevant to the change. Reviewers name the rule when reporting a violation.
`AGENTS.md` routes agents to guidance; `README.md` describes the project.

## Dependency layers

| Rule | What to check |
| --- | --- |
| Keep `paths.py` pure. | Wiring contracts and data-root resolution compute values; filesystem mutation stays in concept modules. |
| Preserve dependencies toward the foundation. | Concept modules build on `paths` and, where needed, `config`; cross-concept lifecycle orchestration stays in `workflows.py`. |
| Keep shared project selection and resource reconciliation in their existing modules. | `projects.py` owns selection and inspection; `assets.py` owns reconciliation shared by lifecycle and asset commands. |
| Keep the CLI thin and load packaged resources through their accessor. | Parsing and rendering stay in `cli.py`; behavior lives in underlying modules; packaged assets are accessed through `resource_loader.py`. |

These boundaries keep filesystem policy, resource delivery, and command presentation
independently testable.

## Subprocesses and verification

| Rule | What to check |
| --- | --- |
| Preserve the injected runner when invoking `bd` or `git`. | Modules accept the existing `run` callable shaped like `subprocess.run`; tests can assert recorded arguments with a fake. |
| Keep tests out of the real home and live data root. | Tests use disposable paths and isolated configuration. |
| Check CLI behavior changes through the supported entry point. | Run affected checks and `uv run pytest`; the entry point is `dotbrain.cli:app`, not `python -m dotbrain`. |

## Code and user data

| Rule | What to check |
| --- | --- |
| Distinguish the source checkout from the data root. | Resolve the data root through `paths.resolve_dotbrain_home()`; global configuration supplies infrastructure defaults and project configuration supplies project selections. |
| Keep user project data private. | Public explanations stand on their own, without private evidence, record identifiers, or operational paths. |

## Managed content

| Rule | What to check |
| --- | --- |
| Keep local wiring untracked. | Symlinks targeting outside the repository and generated runtime resources remain ignored. |
| Preserve user-owned instructions and foreign links during reconciliation. | Changes affect only owned resources or managed blocks; unrelated content remains intact. |
| Keep `AGENTS.md` canonical. | Its sibling `CLAUDE.md` remains a relative symlink to it. |
