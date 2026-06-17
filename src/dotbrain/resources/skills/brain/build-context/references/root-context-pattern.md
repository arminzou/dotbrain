# Root Context Pattern

Use this pattern for workspace-level `AGENTS.md` files.

## What belongs here
- Scope: this file applies only when no nearer context file exists.
- Directory layout: the major top-level folders and what they are for.
- Organization conventions: where repos, notes, infra, and runtime state belong.
- Cross-cutting safety notes: anything that matters across multiple repos.
- Context-file convention: `AGENTS.md` canonical, `CLAUDE.md` symlink, nearest file wins.

## What does not belong here
- Detailed infra/service operations
- Project-specific commands or workflows
- Long inventories that are better maintained in a local repo context
- Repeated detail that causes drift between root and local files

## Good root sections
1. Scope
2. Purpose of the root context
3. Context file convention
4. Top-level directory layout
5. Workspace organization conventions
6. Important cross-cutting notes

## Principle
The root file should orient agents, not try to run every project from one document.
