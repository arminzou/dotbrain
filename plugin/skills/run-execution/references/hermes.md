# Hermes as the lead

Use this reference with the shared contract in [Run Execution](../SKILL.md) when Hermes runs the
lead.

Hermes runs only as the lead. Dotbrain delivers no native Hermes workers, so a Hermes lead does
the writing itself in sequential execution. When the human asks for workers in another runtime,
dispatch them through that runtime's reference, such as [Claude Code](claude-code.md) or
[Codex](codex.md), under the shared contract. Never choose another runtime on your own.

Required reviews, checks and acceptance still apply as the shared contract sets them.
