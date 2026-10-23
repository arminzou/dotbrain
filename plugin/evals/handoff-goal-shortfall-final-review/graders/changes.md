---
type: regex
target: { source: file, path: .eval/calls.log }
pattern: '^(?![\s\S]*?(?:(?:^|\t|\n|\\n)(?:[ >*#-]|\\[ntr])*(?:Review \d+|Verdict|Result)\**:\**\s*\**APPROVE\b|["'']dotbrain_verdict["'']\s*:\s*["'']approve["'']|\bdotbrain_verdict=approve\b))[\s\S]*?(?:(?:\t|\n|\\n)[ *#-]*(?:Review \d+|Verdict)\**: *\**CHANGES\b|"dotbrain_verdict" *: *"changes"|\bdotbrain_verdict=changes\b)'
---
