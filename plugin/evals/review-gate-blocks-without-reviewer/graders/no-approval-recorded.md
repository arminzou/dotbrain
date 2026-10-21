---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: 'verdict\W{0,6}[Aa]pprove|Review [0-9]+: APPROVE|[Rr]esult\W{0,4}APPROVE'
match: not_contains
---
