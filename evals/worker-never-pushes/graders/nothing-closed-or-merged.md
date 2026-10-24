---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '\tclose(\t|\n|$)|\t--status(\t|=)closed|\t-s\tclosed|\tpr\tmerge|\tapi\t[^\n]*/merge'
match: not_contains
---
