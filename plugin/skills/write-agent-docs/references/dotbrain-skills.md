# Writing within dotbrain

Dotbrain gives agent-consumed writing three visibility surfaces. The writing principles in
[`SKILL.md`](../SKILL.md) apply to all three; placement and authority differ.

| Surface | Typical documents | Constraint |
|---|---|---|
| Public project repository | `AGENTS.md`, `CLAUDE.md`, README, architecture, contributor and referenced project docs | Must remain useful without access to the private Brain and contain no private Brain material |
| Private project Brain | `.brain/AGENTS.md`, `CONTEXT.md`, ADRs, designs, and `.brain/docs/` | Holds private vocabulary, decisions, operating rules, and design history; use its established language exactly |
| User data root | Skills under `$DOTBRAIN_HOME/skills/` and their references | Follow the nearest authoring policy; linking and invocation remain explicit operator choices |

Public and private documents may point across the boundary only through the public-safe convention
defined by the project's context workflow. Keep the private rationale in the Brain and express any
publicly necessary reasoning without leaking private paths, identifiers, or operational state.

Use dotbrain's specialized workflows when the task changes structure or lifecycle:

- `curate-project-context` audits and repairs context placement, reachability, drift, and canonical
  `AGENTS.md`/`CLAUDE.md` relationships.
- `to-design`, `iterate-design`, and `close-design` own the design lifecycle.
- `grill-decisions` resolves contested terminology and durable decisions; other active workflows
  may write already-settled vocabulary or promote their own residue using the established formats.

Those workflows determine what belongs in a document and when it changes. The parent skill
determines how the resulting writing retrieves cleanly, directs action, and remains maintainable.
