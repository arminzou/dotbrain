# Readiness review

Run this only before a milestone that will multiply a subsystem's shape: a first consumer, public
API, new client, or rewrite boundary. It is an audit against the project's written decisions, not a
diff review. Use `review-gate readiness` and the shared multi-pass review bead.

## Fix the oracle

Set the standard before looking at code, in this order:

1. Accepted decisions and active designs. List superseded records first; code cannot violate dead
   canon.
2. Stated rules in agent guidance, contributor docs, and enforced configuration. A rule without a
   test or other enforcement is itself a possible gap.
3. Project vocabulary. A public type, route, table, or log field that contradicts settled language
   is a design problem.

Canon silence is not a defect. Record it only when the missing decision blocks the milestone, then
stop for the decision instead of inventing a rule.

## Evidence and severity

Explore freely, but record a finding only with at least traced evidence. Every finding has a
`file:line` location and one tier:

- **E1 — Executed:** command, test, probe, or query output.
- **E2 — Traced:** the relevant path read end-to-end and every caller of the claimed shared behavior
  enumerated.
- **E3 — Canon conflict:** the written rule and contradicting code both quoted with locations.

Below E2 is a lead, not a finding. State what remains unverified rather than upgrading confidence.
Severity is cost to fix after the milestone divided by cost now: `blocker` guarantees rework;
`high` risks data loss or false truth; `medium` is contained; `low` is one line only.

## Passes

Create the multi-pass review bead before pass 1. Append a comment immediately after each pass,
including a clean pass. Choose the order that exposes the next consumer's risk soonest; a useful
default is:

1. Orient: map the subsystem, oracle, and superseded records; record no findings yet.
2. Consumed contract: auth, errors, pagination, status codes, and published request/response shape.
3. Correctness spine: trace one real unit of work through its production path.
4. Persistence and adapter parity: compare behaviors that could silently diverge.
5. Test integrity: prove relevant tests can fail, not merely that coverage exists.
6. Cross-cutting: secrets, configuration/startup validation, observability, and first run.

Keep the reviewed tree untouched. Use real dependencies, direct queries, or a scratch clone for
executed evidence. Stop early and report if investigation would modify the tree, risk data loss, or
expose secrets.

## Test integrity

In a scratch clone, first make a known-covered behavior fail and verify the project gate turns red.
Then test the suspected blind spot (for example, a permissive auth branch or shared default). A
surviving mutation is a finding only after tracing why its detector did not fail. Check the actual
PR-gated tiers as well as main-only tiers.

## Record and close

Each finding states kind (`defect`, `gap`, or `design problem`), severity, area, evidence tier,
locations, relevant canon, concrete failure scenario or deferred cost, evidence, and what remains
unverified. A correction is a later `## Correction:` comment; never rewrite a finding.

The verdict records the readiness call, ordered blockers, and uncovered work. It is not closeout.
At closeout, every finding and uncovered area must be fixed, filed as its own bead, or consciously
declined; append the disposition and verification. When the review also gates a draft PR, add the
`human` label and leave it open until the human gate resolves.
