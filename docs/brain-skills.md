# Brain skills

Brain-coupled skills — the dotbrain system's own operating manual. They either operate a project
control root directly or use its Brain (`.brain/AGENTS.md`, `.brain/CONTEXT.md`, `.brain/adr/`,
`.brain/agents/`) and beads execution state as their working context.

## Role matrix

Every brain pillar has exactly one writing skill; every other skill reads. This keeps each pillar
coherent — no two skills racing to own the same content.

| Skill | Role | AGENTS.md | CONTEXT.md | adr/ | agents/ | beads |
|---|---|---|---|---|---|---|
| wire-brain | provision | structure | structure | structure | structure | init |
| grill-decisions | decide | read | **write** | **write** | — | plan → operate-execution |
| build-context | describe | **write** | read | read | — | — |
| operate-execution | execute | read | read | read | **write** (conventions) | **write** |
| enter-main-agent | activate | read | read | read | read | claim/close |
| triage-public | feed | — | — | — | read | via operate-execution |
| review-architecture | reflect | read | read | read | — | findings → operate-execution |

`wire-brain` provisions the *containers* for all pillars (via the CLI) but writes no
content. `review-architecture` is strictly read-only — its findings route through `grill-decisions`
to become ADRs and through `operate-execution` to become beads.

## Lifecycle

```
wire-brain         ──provisions──→  brain structure
grill-decisions    ──decides─────→  ADRs, CONTEXT.md
build-context      ──describes───→  AGENTS.md
operate-execution      ──executes────→  beads, agents/ conventions
  enter-main-agent   ──activates──→  main-agent mode, optional worker worktrees
  triage-public      ──feeds──────→  public issues → private beads
review-architecture ──reflects────→  findings → grill-decisions + operate-execution
```

The cycle closes when `review-architecture`'s findings feed back into `grill-decisions` (new ADRs)
and `operate-execution` (new beads), restarting the loop.

## Ownership boundaries

**`build-context` owns the brain `AGENTS.md`.** A grilling session *decides* (writes the ADR);
when a decision changes the model, restating it in `AGENTS.md` is `build-context`'s craft.
The decision lives in `adr/`, the model statement in `AGENTS.md`, never the reverse.

**`review-architecture` is strictly read-only.** Its findings are candidate decisions and
candidate work — they never land directly in the brain pillars.

**`agents/` keeps two write modes.** The CLI administers marker keys (`skills.yaml` baseline,
`GitHub intake:`); `operate-execution` owns conventions (e.g. `labels.md`). `triage-public` is a
pure reader of `agents/`.
