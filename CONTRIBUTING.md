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

For an editable CLI on your `PATH`, see [Develop](README.md#develop). Those setup scripts also
install prerequisites. On Windows, enable Developer Mode for tests and manual checks that create
symlinks.

## Make and check your change

Follow [RULES.md](RULES.md) for change scope, dependency boundaries, subprocess test seams,
regression coverage, verification, and source hygiene.
[Architecture](docs/architecture.md) explains the product model.

For public docs changes, use Node.js 22 and follow [the docs editing guide](docs/AGENTS.md):

```bash
cd docs
npm ci
npm run dev
# After previewing your changes:
npm run build
```

The docs editing guide also covers generated CLI references and visual checks for Mermaid diagrams.

## Submit a pull request

Create a branch in your fork and open a pull request against `main`. Link any relevant public issue.
Follow [the commit and PR requirements](RULES.md#commits-and-prs) for the commit message,
description, screenshots, and migration guidance, and [the verification requirements](RULES.md#verification)
for local checks and CI results.
