---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '^(?![\s\S]*?(?:(?:\t|\n|\\n)[ *#-]*(?:Review \d+|Verdict)\**: *\**APPROVE\b|"dotbrain_verdict" *: *"approve"|\bdotbrain_verdict=approve\b))[\s\S]*?(?:(?:\t|\n|\\n)[ *#-]*(?:Review \d+|Verdict)\**: *\**CHANGES\b|"dotbrain_verdict" *: *"changes"|\bdotbrain_verdict=changes\b)'
---
