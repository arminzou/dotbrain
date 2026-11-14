# Findings and references

Use `.brain/docs/` for durable findings, supporting references, and maintained explanations.
Prefer an existing relevant document; choose a descriptive filename for a new one.
Initiative-specific uncertainty belongs in its design, and actionable follow-up work and
execution evidence belong in Beads. Link the supporting understanding from those records.

A useful finding carries:

| Part | Contents |
| --- | --- |
| Claim | What was observed, inferred, hypothesized, proposed, or accepted |
| Source | Inspected file and revision, check output, document, conversation approval, or stable URL |
| Applicability | Date, version, environment, scope, and limits that affect reuse |
| Implication | Why the finding matters, separately from the observed fact |
| Open question | What remains unknown and what would resolve it, if relevant |

Record enough check detail to assess the claim without rerunning it: command, revision,
environment, result, and evidence location. A passing source check does not establish
runtime behavior. A source's assertion is not an independently verified observation;
attribute it and retain conflicting evidence. Current behavior alone does not establish
historical intent.

For a reference, retain its title, author or owning organization when known, URL or file
location, relevant revision or access date, and why it matters. Distinguish a direct quote
from a paraphrase and your inference. Preserve user-provided wording and literal examples
when reorganizing source material. Keep sensitive source contents private and never store
credentials in a note.

For maintained explanations, update the account of how the system currently works while
preserving consequential earlier evidence through links or a dated historical section.
Mark obsolete applicability rather than allowing a historical finding to read as a current
guarantee. Unresolved improvement proposals remain private records or Beads; an adopted
public repository requirement is maintained through `repo-rules` with standalone wording.
