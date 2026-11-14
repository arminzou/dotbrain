# Glossary

| Term | Meaning |
| --- | --- |
| Dotbrain home | Private data root, normally `~/dotbrain`, with configuration, selected resource sources, Brainspaces and its own Git history. |
| Brainspace | A project's private workspace holding `.brain/` knowledge and optional `.beads/` backend state. |
| Brain | Vocabulary, decisions, designs, findings and references in `.brain/`. |
| Brain-only project | A Brainspace without checkout attachment; core tracker opt-out remains available through `beads.mode: none`. |
| ADR | An accepted consequential decision and its rationale, evidence and applicability. A proposal is not an accepted decision. |
| Design | Initiative intent, constraints, uncertainties and verification outcomes. Task status remains in Beads. |
| Work graph | Native Beads tasks, dependencies, claims, acceptance criteria and execution evidence. Readiness expresses dependency eligibility. |
| Home sync | Git versioning and exchange of private home files; separate from Beads backend persistence and backup. |
| Core skill | One of `wire-brain`, `brain-convention`, `maintain-brain`, `work-graph`, or `repo-rules`, usable without pstack. |
| Engineering workflow | The selected procedures for planning, delegation, verification, recovery and delivery, subject to user/repository authority. |
| Pstack mode | Optional Dotbrain-owned `dotbrain-pstack` integration using a pinned external pstack source and project opt-in. |
| Runtime | Claude Code, Codex, Hermes, OpenCode, Pi or Cursor; each has its own integration and limitations. |
| Custom subagent | An operator-selected Claude Code or Codex definition; the core ships no workflow agents. |
| Worktree | An isolated Git checkout that can share the existing Brainspace while receiving checkout-local runtime resources. |
| Adopted requirement | Public repository policy, normally in `RULES.md`, maintained separately from proposed improvements. |
| Agent routing | Concise `AGENTS.md` pointers to repository requirements and task-relevant guidance. |
| Derive | Write fresh public guidance from accepted understanding without exposing private sources, paths or identifiers. |
| Structural verification | Checks of source identity, packaged files, delivery and configuration; does not prove native agent use. |
| Native qualification | Observed runtime behavior with exact revisions, versions, settings and inspectable evidence. |

See [Architecture](architecture.md), [configuration](configuration.md), and
[workflow selection](workflow.md) for the owning contracts.
