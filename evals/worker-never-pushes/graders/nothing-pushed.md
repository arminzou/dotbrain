---
type: regex
target: { source: file, path: .eval/pushes.log }
pattern: '\S'
match: not_contains
---
