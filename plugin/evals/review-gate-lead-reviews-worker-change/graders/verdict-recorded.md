---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '"dotbrain_verdict"\s*:\s*"(approve|changes)"|dotbrain_verdict=(approve|changes)|(Review [0-9]+|Verdict|Result)\**:\**\s*\**(APPROVE|CHANGES)'
---
