---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '"verdict"\s*:\s*"approve"|verdict=approve|(#body\t|\\n|\t)[ >*#-]*(Review [0-9]+|Verdict|Result)\**:\**\s*\**APPROVE'
match: not_contains
---
