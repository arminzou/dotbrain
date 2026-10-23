---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?m)^bd\t[^\n]*\tcomments\tadd\tdemo-2\t[^\n]*--actor(\t|=)worker-a[^\n]*\n#body\t## Candidate @ [0-9a-f]{7,}'
---
