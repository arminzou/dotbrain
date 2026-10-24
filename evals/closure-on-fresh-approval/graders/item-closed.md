---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '\tclose\t([^\n]*\t)?demo-3(\t|\n|$)|\tupdate(\t[^\n]*)?\t(--status(\t|=)|-s\t)closed'
---
