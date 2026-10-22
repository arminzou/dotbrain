# Cursor as the lead

Use this reference with the shared contract in [Run Execution](../SKILL.md) when Cursor runs the lead.

Cursor runs only as the lead. Dotbrain delivers no native Cursor workers, so a Cursor lead does
the writing itself in sequential execution. When the human asks for workers in another runtime,
dispatch them through that runtime's reference, such as [Claude Code](claude-code.md) or
[Codex](codex.md), under the shared contract. Never choose another runtime on your own.

Cursor CLI discovery and manual-only invocation remain subject to native qualification.
