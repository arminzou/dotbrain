# Evaluation

Use [the native catalog journey](native/README.md) for current evaluation of the
workflow-independent core and selected pstack integration. From the repository
root, run its default model-free calibration:

```sh
uv run python -B -m unittest discover -s evals/native -v
```

The calibration uses synthetic native records and injected boundaries. It needs
no Node.js packages, Promptfoo, Claude SDK, sign-in, or model calls. Optional
real-backend and process checks are described in the native guide. Calibration
proves the measurement gate, not native loading, integration behavior, or a
successful qualification run.

The native guide describes fixture preparation, supported resource delivery,
explicitly authorized native execution, verification, and evidence export.
Native calls require its separate authorization gate and preserve prior attempts
and allowances. Missing or held evidence remains unqualified.

The former packaged-workflow suite is a [frozen historical archive](legacy/README.md).
Its providers, cases, dependency locks, and original guidance remain inspectable;
they are not current entrypoints or qualification evidence for the redesigned
product. Existing ignored `results/` and `node_modules/` remain in place and are
not migrated or reused by the current calibration.
