# Architecture

This page explains dotbrain's design: Brainspaces, the split between the Brain and execution,
skills, and the public/private boundary.

## The Big Picture

```mermaid
flowchart TB
  accTitle: How dotbrain, the code repo, and the private Brainspace connect
  subgraph tool["Public: the dotbrain tool"]
    direction LR
    plugin["`**Plugin**
  skills, convention, hook`"]
    cli["`**CLI**
  wire, refresh, doctor`"]
  end
  agent(["Coding agent"])
  subgraph repo["Your code repo"]
    direction LR
    code["source code"]
    links["`***.brain***, ***.beads***
  gitignored links`"]
  end
  subgraph home["`Private: *~/dotbrain/brainspaces/my-app*`"]
    direction LR
    brain["`***.brain/***
  knowledge`"]
    beads["`***.beads/***
  execution`"]
  end
  plugin -- "injects context" --> agent
  cli -- wires --> links
  agent --> code
  agent -- "reads and writes" --> links
  links -. symlinks .-> home
```

Three parts, three owners:

- **The tool** is public and the same for everyone.
- **The dotbrain home** is yours and private. It holds every project's Brainspace and is versioned
  as one Git repository.
- **The code repo** stays the code repo. It gains ignored local wiring and generated runtime assets.

## Brainspaces

A **Brainspace** is one directory per project that holds everything an agent needs that is not the
code itself:

- `.brain/` is the project's knowledge.
- `.beads/` is the execution store: issues, dependencies, and plans.

The code repo reaches its Brainspace through the gitignored `.brain` and `.beads` symlinks. Its
`.claude` and `.codex` agent workspaces are real directories; dotbrain adds individually ignored
skill links, Claude agent links, and marked Codex agent files without claiming project-owned
files. The agent sees one tree, the repo
stays clean, and the context stays private. [Wiring](wiring.md) covers the details.

## The Brain

Each element of a Brain has one purpose:

```mermaid
treeView-beta
  accTitle: The files and folders of a Brain
  .brain/
    CONTEXT.md ## domain vocabulary
    adr/ ## decision records
    designs/ ## one design doc per initiative
    AGENTS.md ## this project's agent conventions
    DOTBRAIN.md ## shared convention, owned by dotbrain
    project.yaml ## runtime, tracker, skill selection
    docs/ ## derived runbooks and reference
    learning/ ## optional learning workspace
```

| Element | Holds | Changes when |
| --- | --- | --- |
| `CONTEXT.md` | Domain vocabulary: the names issues, plans, and code use | A concept is named or sharpened |
| `adr/` | Architecture Decision Records, one per decision | A hard-to-reverse choice with a real trade-off is made |
| `designs/` | Design docs, one initiative per file | An initiative is planned, built, or closed |
| `AGENTS.md` | This project's agent conventions | Working rules change |
| `DOTBRAIN.md` | The shared convention, owned by dotbrain | `dotbrain refresh` updates it |
| `project.yaml` | Runtime, tracker, skill, and subagent selection | You change what the project uses |
| `docs/` | Derived runbooks and reference | Anytime; never authoritative |
| `learning/` | Optional learning workspace for the operator | You learn the project with `teach-me` |

ADRs record decisions that are hard to reverse, surprising without context, and the result of a
real trade-off. An **active** design is the living authority for its initiative; once it is
**shipped**, **abandoned**, or **superseded** it freezes as a record, and what should outlive it
moves to `adr/` and `CONTEXT.md`. [The workflow](workflow.md) walks through that lifecycle.

Brain writes are commits in the dotbrain home, so every change can be reviewed and reverted.

## Execution Lives in the Tracker

Plans and tasks do not live in markdown checklists that go stale. They live in an **execution
store**, by default [Beads](https://github.com/gastownhall/beads), a dependency-aware issue tracker.
Multi-step work is an epic with `blocks` dependencies, so "what is ready" is a query:

```mermaid
flowchart LR
  accTitle: A design doc and its epic of dependent issues
  d["`**Design doc**
  the spec`"] -. "spec-id" .- e["epic"]
  e --> t1["issue A"]
  e --> t2["issue B"]
  e --> t3["issue C"]
  t1 -- blocks --> t3
  t2 -- blocks --> t3
```

The design says where to go; the tracker says where you are. The store is machine-local runtime
state hydrated from configuration, so the same project can run embedded on one machine or against a
shared server. See [Beads backend](beads-backend.md).

## Skills

Skills are reusable agent capabilities owned by the tool, not by a project. The plugin ships the
Brain-coupled skills; dotbrain links only the operator's own global and per-project selections.

Linking is idempotent: dotbrain creates and prunes only the links it owns. It never deletes a real
file or a link it did not create, which lets bundled skills coexist with private ones on the same
machine. See [Skills](skills.md).

## Session Start

A one-time `dotbrain bootstrap` prepares global skills and subagents. After that, every agent session
in a wired repo starts with the dotbrain convention injected by the plugin's hook, so the agent
already knows where the Brain is and how to use it. See [Session context](session-context.md).

## The Public/Private Boundary

The decision that shapes everything: **the tool is public; your data is private.**

- This repository is the tool: CLI, plugin, skills, templates.
- Your Brainspaces live in a separate data root the installed tool operates on.
- The tool never contains project data, and a Brain is never mirrored into a code repo.
- When something needs to be public, you **derive** a fresh document for that audience instead of
  exposing the private source.

That boundary is what lets the same open-source tool serve entirely private work.
