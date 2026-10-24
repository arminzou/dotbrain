---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?mi)^bd\t[^\n]*\tcomments\tadd\tdemo-2\t[^\n]*--actor(?:\t|=)worker-a[^\n]*\n#body\t## Candidate @ ([0-9a-f]{7,})[0-9a-f]*\\n(?:\\n)?\*\*Status:\*\* DONE[^\n]{1,5}\*\*Observed:\*\* \1[^\n]*\*\*Candidate:\*\*[^\n]*contributing-guide[^\n]*\*\*Checks:\*\*[^\n]*make test[^\n]*pass'
---
