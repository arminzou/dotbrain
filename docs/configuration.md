# Configuration

dotbrain has two user-edited config files:

- `~/dotbrain/config.yaml` for machine-wide defaults
- `~/dotbrain/brainspaces/<name>/.brain/project.yaml` for per-project settings

`dotbrain bootstrap` seeds `config.yaml`. `dotbrain wire` seeds each project's `project.yaml`.

## `config.yaml`

Use `config.yaml` for shared infrastructure defaults. Most installations can leave the `beads`
server block commented out and stay on embedded beads storage.

```yaml
version: 3

# Shared defaults for server-mode beads projects.
beads:
  server:
    host: db.example.internal
    port: "3307"
    user: beads
    # Optional SSH hop for commands that need to reach the sql-server.
    ssh_host: bastion.example.internal
```

## `project.yaml`

Use `project.yaml` for project identity and local deviations from the global defaults.

```yaml
execution-engine: beads

agents:
  - claude
  - codex

public-tracker: gh
public-tracker-id: owner/repo

beads:
  mode: server
  remote: https://doltremoteapi.dolthub.com/owner/repo
  database: project_beads

skills:
  - some-collection/some-skill
```

## Notes

- `beads.mode` is usually `embedded`. Switch to `server` only when the project should use a shared
  Dolt sql-server.
- `beads.remote` and `beads.database` are project-level overrides. Leave them out unless the
  project should deviate from the default naming/layout.
- `agents` controls which agent workspaces dotbrain seeds for the project.
- `skills` adds project-specific skills on top of dotbrain's required core skills.
- `public-tracker` configures public issue intake and contributor collaboration. It does not mirror
  the private execution graph or cause private work items to become public issues.
