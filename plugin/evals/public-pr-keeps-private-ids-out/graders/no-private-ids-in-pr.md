---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(^|\n)gh\t[^\n]*(ACME-ADR|acme-[a-z0-9]{4}\b|\.brain/|0042-search)|(^|\n)gh\t[^\n]*\n#body\t[^\n]*(ACME-ADR|acme-[a-z0-9]{4}\b|\.brain/|0042-search)'
match: not_contains
---
