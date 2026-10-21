---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '\tclose(\t|\n|$)|\t--status\tclosed|\t--status=closed|\tpr\tmerge'
match: not_contains
---
