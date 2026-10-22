---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '"verdict"\s*:\s*"(approve|changes)"|verdict=(approve|changes)|(Review [0-9]+|Verdict|Result)\**:\**\s*\**(APPROVE|CHANGES)'
---
