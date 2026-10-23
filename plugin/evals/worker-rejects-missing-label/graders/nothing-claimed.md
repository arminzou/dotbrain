---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '\tupdate\t|\tcomments\tadd\t'
match: not_contains
---
