# Documentation

Source for the public docs site at <https://arminzou.github.io/dotbrain/>. Each page also reads
fine on GitHub.

## Guide

- [why-dotbrain.md](why-dotbrain.md) — candid comparisons, trade-offs, and when to skip it.
- [getting-started.md](getting-started.md) — install, wire a repo, and verify the result.
- [prompts.md](prompts.md) — example prompts for each common job, and the skill each triggers.

## Use Cases

- [workflow.md](workflow.md) — develop a project from first idea to closed design, one skill per step.
- [agent-team.md](agent-team.md) — HITL and handoff, sequential and parallel work, and packaged subagents.
- [learning.md](learning.md) — learn across sessions, park concepts, and capture demonstrated understanding.
- [brain-site.md](brain-site.md) — read, search, and navigate the private Brain.

## How It Works

- [architecture.md](architecture.md) — Brainspaces, the Brain/execution split, the public/private boundary.
- [wiring.md](wiring.md) — what gets linked, and when to wire, refresh, or unwire.
- [session-context.md](session-context.md) — what the agent knows at session start.
- [beads-backend.md](beads-backend.md) — embedded and server tracker modes.

## Reference

- [cli-reference.md](cli-reference.md) — generated; regenerate with `uv run python -m dotbrain._cli_reference`.
- [configuration.md](configuration.md) — every config file and key.
- [brain-site-configuration.md](brain-site-configuration.md) — set up and customize the private Brain site.
- [skills.md](skills.md) — the bundled Brain-coupled skills.
- [glossary.md](glossary.md) — the dotbrain vocabulary.
- [troubleshooting.md](troubleshooting.md) — common problems and FAQ.

## Local Preview

```bash
cd docs && npm ci && npm run dev
```
