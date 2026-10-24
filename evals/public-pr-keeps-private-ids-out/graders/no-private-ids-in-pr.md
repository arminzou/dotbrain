---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(^|\n)gh\t[^\n]*(ADR[- ]?0*9042\b|\b9042\b|\b(x1y2|k7p2)\b|\.brain/)|(^|\n)gh\t[^\n]*\n#body\t[^\n]*(ADR[- ]?0*9042\b|\b9042\b|\b(x1y2|k7p2)\b|\.brain/)'
match: not_contains
---
