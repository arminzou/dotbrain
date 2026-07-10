# CLI Reference

Reference for the public `dotbrain` CLI.

## `dotbrain`

```text
                                                                                
 Usage: dotbrain [OPTIONS] COMMAND [ARGS]...                                    
                                                                                
 dotbrain CLI for wiring project Brainspaces and skills into coding agents.     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion            Install completion for the current shell.    │
│ --show-completion               Show completion for the current shell, to    │
│                                 copy it or customize the installation.       │
│ --help                -h        Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ bootstrap  Prepare this machine for dotbrain: global hooks and global skill  │
│            links.                                                            │
│ doctor     Read-only health check: machine readiness, project wiring, beads  │
│            state drift.                                                      │
│ wire       Create or repair a project Brainspace and wire an adopter repo.   │
│ refresh    Refresh Brain/workspace files, repo links, beads state, and       │
│            project skills.                                                   │
│ unwire     Disconnect an adopter repo from its Brainspace.                   │
│ archive    Archive a Brainspace into archive/ after disconnecting any        │
│            adopter repo wiring.                                              │
│ unarchive  Restore an archived Brainspace into the active brainspaces/       │
│            registry without rewiring it.                                     │
│ codex      Create or reuse a dotbrain-wired git worktree and start Codex     │
│            there.                                                            │
│ skills     Link dotbrain skills into agent runtimes.                         │
│ agents     Link dotbrain vendor-native subagents into agent runtimes.        │
│ beads      Manage beads tracker state and backend.                           │
│ hook       Run dotbrain hook entrypoints.                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain agents`

```text
                                                                                
 Usage: dotbrain agents [OPTIONS] COMMAND [ARGS]...                             
                                                                                
 Link dotbrain vendor-native subagents into agent runtimes.                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ link                                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain agents link`

```text
                                                                                
 Usage: dotbrain agents link [OPTIONS]                                          
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --target           TEXT  claude-code | codex | all [default: all]            │
│ --scope            TEXT  global | project | all [default: all]               │
│ --project          TEXT  Limit project linking to a single Brainspace by     │
│                          name.                                               │
│ --help     -h            Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain archive`

```text
                                                                                
 Usage: dotbrain archive [OPTIONS]                                              
                                                                                
 Archive a Brainspace into archive/ after disconnecting any adopter repo        
 wiring.                                                                        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --repo             PATH  Adopter repo path; defaults to cwd.                 │
│ --name             TEXT  Project/Brainspace name.                            │
│ --no-repo                Archive the named Brainspace only; do not edit an   │
│                          adopter repo.                                       │
│ --dry-run                Preview the archive without performing it.          │
│ --help     -h            Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain beads`

```text
                                                                                
 Usage: dotbrain beads [OPTIONS] COMMAND [ARGS]...                              
                                                                                
 Manage beads tracker state and backend.                                        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ drop-db  Drop a project's remote beads database on the shared Dolt           │
│          sql-server.                                                         │
│ list-db  List the databases on the shared Dolt sql-server.                   │
│ migrate  Migrate a local-only (embedded Dolt) beads tracker onto the remote  │
│          sql-server, history intact.                                         │
│ load     Hydrate local beads state from tracked declarations: attach server  │
│          trackers, init embedded                                             │
│          ones, then pull. Pull-only reconcile: never pushes, never touches   │
│          symlinks or hooks.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain beads drop-db`

```text
                                                                                
 Usage: dotbrain beads drop-db [OPTIONS] NAME                                   
                                                                                
 Drop a project's remote beads database on the shared Dolt sql-server.          
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Beads database name to drop (usually the project name). │
│                      [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --yes                              Confirm the destructive drop.             │
│ --dry-run                          Preview the drop without running it.      │
│ --beads-ssh-host             TEXT  SSH hop that can reach the sql-server;    │
│                                    empty connects directly. Defaults to      │
│                                    beads.server.ssh_host.                    │
│ --beads-server-host          TEXT  Dolt sql-server host. Defaults to         │
│                                    beads.server.host.                        │
│ --beads-server-port          TEXT  Dolt sql-server port. Defaults to         │
│                                    beads.server.port.                        │
│ --beads-server-user          TEXT  Dolt sql-server user. Defaults to         │
│                                    beads.server.user.                        │
│ --help               -h            Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain beads list-db`

```text
                                                                                
 Usage: dotbrain beads list-db [OPTIONS]                                        
                                                                                
 List the databases on the shared Dolt sql-server.                              
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --beads-ssh-host             TEXT  SSH hop that can reach the sql-server;    │
│                                    empty connects directly. Defaults to      │
│                                    beads.server.ssh_host.                    │
│ --beads-server-host          TEXT  Dolt sql-server host. Defaults to         │
│                                    beads.server.host.                        │
│ --beads-server-port          TEXT  Dolt sql-server port. Defaults to         │
│                                    beads.server.port.                        │
│ --beads-server-user          TEXT  Dolt sql-server user. Defaults to         │
│                                    beads.server.user.                        │
│ --help               -h            Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain beads load`

```text
                                                                                
 Usage: dotbrain beads load [OPTIONS]                                           
                                                                                
 Hydrate local beads state from tracked declarations: attach server trackers,   
 init embedded ones, then pull. Pull-only reconcile: never pushes, never        
 touches symlinks or hooks.                                                     
                                                                                
 Without --all: load one project (by --name, or the --repo/cwd repo). With      
 --all: every brainspace                                                        
 root declared to use beads.                                                    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all                     Load tracker state for every Brainspace.           │
│ --repo              TEXT  Repo whose Brainspace to load. Defaults to the     │
│                           current git repo.                                  │
│ --name              TEXT  Project/Brainspace name to load.                   │
│ --dotbrain          TEXT  dotbrain checkout. Defaults to                     │
│                           $DOTBRAIN_HOME/inferred.                           │
│ --dry-run                 Preview what would be hydrated/pulled without      │
│                           mutating anything.                                 │
│ --help      -h            Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain beads migrate`

```text
                                                                                
 Usage: dotbrain beads migrate [OPTIONS]                                        
                                                                                
 Migrate a local-only (embedded Dolt) beads tracker onto the remote sql-server, 
 history intact.                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --repo                       TEXT  Wired repo path; project name is its dir  │
│                                    name.                                     │
│ --name                       TEXT  Project/Brainspace name to migrate.       │
│ --all                              Migrate every embedded Brainspace.        │
│ --dotbrain                   TEXT  dotbrain checkout. Defaults to            │
│                                    $DOTBRAIN_HOME/inferred.                  │
│ --beads-server-host          TEXT  Target Dolt sql-server host. Defaults to  │
│                                    beads.server.host in config.yaml.         │
│ --beads-server-port          TEXT  Dolt sql-server port. Defaults to         │
│                                    beads.server.port in config.yaml.         │
│ --beads-server-user          TEXT  Dolt sql-server user. Defaults to         │
│                                    beads.server.user in config.yaml.         │
│ --beads-database             TEXT  Dolt database name (single-project only). │
│                                    Defaults to project name.                 │
│ --dry-run                          Print the planned bd sequence without     │
│                                    running it.                               │
│ --help               -h            Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain bootstrap`

```text
                                                                                
 Usage: dotbrain bootstrap [OPTIONS]                                            
                                                                                
 Prepare this machine for dotbrain: global hooks and global skill links.        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --only                      TEXT  claude-hook | codex-hook | skills          │
│ --skip-claude-hook                                                           │
│ --skip-codex-hook                                                            │
│ --skip-skills                                                                │
│ --help              -h            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain codex`

```text
                                                                                
 Usage: dotbrain codex [OPTIONS]                                                
                                                                                
 Create or reuse a dotbrain-wired git worktree and start Codex there.           
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --worktree   -w      TEXT  Branch/worktree name, e.g. feature-auth        │
│                               [required]                                     │
│    --repo       -C      PATH  Repo path; defaults to the current git repo    │
│    --base               TEXT  Base ref for a new worktree [default: main]    │
│    --prompt             TEXT  Initial Codex prompt                           │
│    --codex-arg          TEXT  Extra argument passed to Codex; repeatable     │
│    --print                    Print commands instead of running them         │
│    --help       -h            Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain doctor`

```text
                                                                                
 Usage: dotbrain doctor [OPTIONS]                                               
                                                                                
 Read-only health check: machine readiness, project wiring, beads state drift.  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain hook`

```text
                                                                                
 Usage: dotbrain hook [OPTIONS] COMMAND [ARGS]...                               
                                                                                
 Run dotbrain hook entrypoints.                                                 
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ session-start              Run the dotbrain SessionStart hook.               │
│ claude-worktree-bootstrap  Run the global Claude first-worktree bootstrap    │
│                            hook.                                             │
│ codex-worktree-bootstrap   Run the global Codex first-worktree bootstrap     │
│                            hook.                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain hook claude-worktree-bootstrap`

```text
                                                                                
 Usage: dotbrain hook claude-worktree-bootstrap [OPTIONS] [ARGS]...             
                                                                                
 Run the global Claude first-worktree bootstrap hook.                           
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   args      [ARGS]...                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain hook codex-worktree-bootstrap`

```text
                                                                                
 Usage: dotbrain hook codex-worktree-bootstrap [OPTIONS] [ARGS]...              
                                                                                
 Run the global Codex first-worktree bootstrap hook.                            
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   args      [ARGS]...                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain hook session-start`

```text
                                                                                
 Usage: dotbrain hook session-start [OPTIONS] [ARGS]...                         
                                                                                
 Run the dotbrain SessionStart hook.                                            
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   args      [ARGS]...                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain refresh`

```text
                                                                                
 Usage: dotbrain refresh [OPTIONS]                                              
                                                                                
 Refresh Brain/workspace files, repo links, beads state, and project skills.    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all                      Refresh every project workspace.                  │
│ --name               TEXT  Refresh one project by Brainspace name.           │
│ --repo-base          PATH  Base directory for repo discovery.                │
│ --help       -h            Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain skills`

```text
                                                                                
 Usage: dotbrain skills [OPTIONS] COMMAND [ARGS]...                             
                                                                                
 Link dotbrain skills into agent runtimes.                                      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ link  Link skills into agent runtimes.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain skills link`

```text
                                                                                
 Usage: dotbrain skills link [OPTIONS]                                          
                                                                                
 Link skills into agent runtimes.                                               
                                                                                
 Both scopes are curated include-lists. Project links the brain-coupled         
 required core plus each project's ``project.yaml`` ``skills:`` extras into its 
 agent workspaces. Global links the required core plus optional operator        
 extras into each runtime's global skills dir.                                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --target           TEXT  claude-code | codex | all [default: all]            │
│ --scope            TEXT  global | project | all [default: all]               │
│ --project          TEXT  limit project scope to one Brainspace by name       │
│ --help     -h            Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain unarchive`

```text
                                                                                
 Usage: dotbrain unarchive [OPTIONS] NAME                                       
                                                                                
 Restore an archived Brainspace into the active brainspaces/ registry without   
 rewiring it.                                                                   
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Project/Brainspace name to restore from archive/.       │
│                      [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run            Preview the restore without performing it.              │
│ --help     -h        Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain unwire`

```text
                                                                                
 Usage: dotbrain unwire [OPTIONS]                                               
                                                                                
 Disconnect an adopter repo from its Brainspace.                                
                                                                                
 Offboards the Brainspace only (keep/archive/delete). For explicit lifecycle    
 commands, prefer                                                               
 `dotbrain archive` and `dotbrain unarchive`. To drop a server-backend          
 project's remote beads                                                         
 database, use `dotbrain beads drop-db` separately.                             
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all                    Unwire every project Brainspace (keep only; see     │
│                          per-project --archive/--delete for destructive      │
│                          offboard).                                          │
│ --repo             PATH  Adopter repo path; defaults to cwd                  │
│ --name             TEXT  Project/Brainspace name                             │
│ --no-repo                Only offboard the named Brainspace; do not edit an  │
│                          adopter repo.                                       │
│ --archive                Move Brainspace to archive/ (compatibility path;    │
│                          prefer `dotbrain archive`).                         │
│ --delete                 Remove the Brainspace (destructive)                 │
│ --dry-run                Preview the offboard without performing it.         │
│ --help     -h            Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## `dotbrain wire`

```text
                                                                                
 Usage: dotbrain wire [OPTIONS]                                                 
                                                                                
 Create or repair a project Brainspace and wire an adopter repo.                
                                                                                
 Without --all: wire one project. With --all: reconcile every Brainspace.       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all                                Wire every adopter repo to its          │
│                                      Brainspace (brain seeding, symlinks,    │
│                                      hooks).                                 │
│ --repo                         TEXT  Repo to wire. Defaults to the current   │
│                                      git repo.                               │
│ --name                         TEXT  Project/Brainspace name. Defaults to    │
│                                      repo dir name.                          │
│ --dotbrain                     TEXT  dotbrain checkout. Defaults to          │
│                                      $DOTBRAIN_HOME/inferred.                │
│ --skip-beads                         Do not initialize .beads when missing.  │
│ --install-global-hook                Also install the global Claude          │
│                                      SessionStart hook. Prefer `dotbrain     │
│                                      bootstrap` for machine setup.           │
│ --beads-remote                 TEXT  Initialize beads from this Dolt remote. │
│ --beads-server-host            TEXT  Init beads against an external Dolt     │
│                                      sql-server. Defaults to                 │
│                                      beads.server.host in config.yaml.       │
│ --beads-server-port            TEXT  Dolt sql-server port. Defaults to       │
│                                      beads.server.port in config.yaml.       │
│ --beads-server-user            TEXT  Dolt sql-server user. Defaults to       │
│                                      beads.server.user in config.yaml.       │
│ --beads-database               TEXT  Dolt database name. Defaults to project │
│                                      name.                                   │
│ --no-repo                            Create a brain-only Brainspace (no code │
│                                      repo). Requires --name.                 │
│ --repo-base                    PATH  Base directory for adopter repos        │
│                                      (default: ~/repos/projects).            │
│ --help                 -h            Show this message and exit.             │
╰──────────────────────────────────────────────────────────────────────────────╯
```
