---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '(?:^|\t|\n)[ >*#-]*(?:Review \d+|Verdict)\**: *\**CHANGES\b|"dotbrain_verdict" *: *"changes"|\bdotbrain_verdict=changes\b'
---
