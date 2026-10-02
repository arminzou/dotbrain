# Contributing to dotbrain

Bug reports, documentation corrections, and focused pull requests are welcome.

## Report a bug or propose a change

Use [GitHub Issues](https://github.com/arminzou/dotbrain/issues). For bugs, include your operating
system, dotbrain version, agent runtime, the command or steps you ran, and expected versus actual
behavior. Include relevant output with credentials and private project information removed.

For larger features or changes to CLI behavior, start with an issue to discuss the scope before
implementing. Small fixes can go directly to a pull request.

## Set up a checkout

Install [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Dotbrain requires Python 3.11 or later; uv can provision a compatible Python version.

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
uv sync
uv run dotbrain --help
uv run pytest
```

You can develop and run tests without wiring this checkout to a Brainspace or installing an
agent plugin. Tests use temporary directories rather than your live data root or runtime homes.
For Beads integration checks, install `bd` from [Beads](https://github.com/gastownhall/beads);
CI installs it on Linux, macOS, and Windows.

For an editable CLI on your `PATH`, see [Develop](README.md#develop). Those setup scripts also
install prerequisites. On Windows, enable Developer Mode for tests and manual checks that create
symlinks.

## Make and check your change

Keep each pull request focused. Follow the dependency layering and subprocess test seams described
in [AGENTS.md](AGENTS.md); [Architecture](docs/architecture.md) explains the product model.
Add a regression test for a behavior fix where practical. Run the affected tests while iterating
and `uv run pytest` before submitting code changes. There is no configured linter.

For public docs changes, use Node.js 22 and follow [the docs editing guide](docs/AGENTS.md):

```bash
cd docs
npm ci
npm run dev
# After previewing your changes:
npm run build
```

Mermaid diagrams render in the browser, so check them visually in both light and dark themes;
a successful build alone does not verify them. For CLI help changes, regenerate the reference
from the repo root with `uv run python -m dotbrain._cli_reference`.

Keep contributions useful without the maintainer's private context. Include only public tool
source, packaged templates, and documentation; exclude personal Brainspaces, execution stores,
runtime wiring, credentials, and private tracker or decision identifiers.

## Submit a pull request

Create a branch in your fork and open a pull request against `main`. Explain the problem,
the resulting behavior, and how you verified it. Include before/after screenshots for visual
changes and link any relevant public issue. Call out changes to command syntax or JSON output
and explain how users should migrate.

Use the repository's Conventional Commit style for commit messages, such as
`fix(cli): explain invalid project selection` or `docs: clarify installation steps`.
CI runs the Python test suite on Linux, macOS, and Windows. Check its results and address failures
before asking for review.
