---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?:^|\n)(?:bd|#body)\t(?![^\n]*\bAPPROVE\b)(?=[^\n]*\b(?:[Ss]ettings|[Dd]ark)\b)(?=[^\n]*(?:[Ss]hortfall|[Gg]oal[^\n]{0,60}\b(?:unmet|not met|not delivered|not honou?red|missed)\b))[^\n]+'
---
