---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(^|\n)gh\t[^\n]*(ADR[- ]?0*42\b|\b(x1y2|k7p2)\b|\.brain/|0042-search)|(^|\n)gh\t[^\n]*\n#body\t[^\n]*(ADR[- ]?0*42\b|\b(x1y2|k7p2)\b|\.brain/|0042-search)'
match: not_contains
---
