---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?:^|\t|\n)[ >*#-]*(?:Review \d+|Verdict)\**: *\**CHANGES\b|"verdict" *: *"changes"|\bverdict=changes\b'
---
