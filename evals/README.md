# Evaluation

[Record placement](records/README.md) evaluates the workflow-independent core
with a stock skill workflow: plans land in Beads, reasoning in the Brain, nothing
in the repository, and a cold session resumes from `bd ready`. From the repository
root, run its model-free calibration:

```sh
cd evals/records && uv run python -B -m unittest -v test_records
```

Calibration needs no sign-in or model calls and proves the grader, not agent
behavior. Native runs need explicit `--allow-native`; see the guide.

The former packaged-workflow suite is a [frozen historical archive](legacy/README.md).
The native catalog journey, which qualified the retired pstack adapter's coordinator
procedure, is available in Git history at revision `3fbafb2`
(`git show 3fbafb2:evals/native/README.md`). Neither is a current entrypoint.
Existing ignored `results/` and `node_modules/` remain in place.
