# agents/

Per-project agent operating conventions the agent reads while working.

- `issue-tracker.md` — project conventions shared by `operate-execution` and `triage-public`:
  linking rules, ADR policy, priority deviations. Empty means pure defaults.

CLI mechanics for a specific engine or tracker (e.g. `bd`, `gh`) are *not* kept here — they ship
with the owning skill and are selected via `project.yaml` (`execution-engine:`, `public-tracker:`).
Skill *selection* is likewise not configured here; per-project skills live in `project.yaml` under
`skills:`.

See `DOTBRAIN.md` for the read order and operating rules.
