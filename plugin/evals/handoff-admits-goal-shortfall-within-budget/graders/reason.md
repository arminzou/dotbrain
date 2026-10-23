---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?:^|\n)bd\t[^\n]*?\t(?:create|update|close)\t[^\n]*?\t(?:--description|--notes|--append-notes|--reason|--body|-d)(?:\t|=)(?![^\t\n]*\bAPPROVE\b)(?=[^\t\n]*\b(?:[Ss]ettings|[Dd]ark)\b)(?=[^\t\n]*(?:[Ss]hortfall|[Gg]oal[^\t\n]{0,60}\b(?:unmet|not met|not delivered|not honou?red|missed)\b))[^\t\n]+|(?:^|\n)bd\t[^\n]*?\tcomments?\t(?:add\t)?[^\t\n]+\t(?![^\t\n]*\bAPPROVE\b)(?=[^\t\n]*\b(?:[Ss]ettings|[Dd]ark)\b)(?=[^\t\n]*(?:[Ss]hortfall|[Gg]oal[^\t\n]{0,60}\b(?:unmet|not met|not delivered|not honou?red|missed)\b))[^\t\n]+|(?:^|\n)#body\t(?![^\t\n]*\bAPPROVE\b)(?=[^\t\n]*\b(?:[Ss]ettings|[Dd]ark)\b)(?=[^\t\n]*(?:[Ss]hortfall|[Gg]oal[^\t\n]{0,60}\b(?:unmet|not met|not delivered|not honou?red|missed)\b))[^\t\n]+'
---
