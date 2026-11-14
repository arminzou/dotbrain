# Example prompts

Ask for the operation you need. The five core skills maintain workspace resources,
project understanding, requirements and work records. Engineering implementation
goes to your chosen workflow. Use the skill names your runtime exposes; Claude
Code plugin commands use `/dotbrain:<name>`, while Codex exposes them in its picker.

## Wire or repair a repository

```text
Use wire-brain to wire this repository with Dotbrain and check its health.
```

`wire-brain` handles setup and repair through the CLI. Wiring alone selects no
pstack mode. See [Getting started](getting-started.md).

## Capture project understanding

```text
Use maintain-brain to record the verified API constraint and its evidence.
Keep the retry explanation as an unresolved hypothesis.
```

Use the same capability to maintain vocabulary, accepted decisions, designs,
references, and lifecycle records. Capturing a finding adopts no new decision;
terminal lifecycle claims require evidence and authority.

## Inspect or maintain work records

```text
Use work-graph to inspect this initiative's dependencies and current ownership.
Report ready work without starting implementation or changing claims.
```

For authorized writes, specify the task operation and applicable actor. Native
Beads readiness is dependency eligibility; the chosen workflow applies scope,
capacity and acceptance. See [Beads backend](beads-backend.md).

## Initialize repository requirements

```text
Use repo-rules to initialize RULES.md and its AGENTS.md routing.
Adapt the baseline to this repository, preserve existing requirements,
and report conflicts without adopting a resolution.
```

Initialization is requested explicitly. A bare invocation assesses; it does not
adopt proposed requirements or create a rules file. Public `AGENTS.md` routes to
the requirements rather than duplicating them.

## Assess enforcement

```text
Use repo-rules to assess enforcement of the adopted dependency boundary.
Report the existing checks and smallest enforcement gap without editing files.
```

Requested enforcement implementation is handed to the selected engineering
workflow with the adopted rule, authority, affected boundary and checks, proposed
mechanism, and verification needs. Assessment itself changes no code, lint or CI.

## Use a selected engineering workflow

After [explicit pstack setup](workflow.md#opt-in), start a fresh session and select
the displayed `dotbrain-pstack` skill:

```text
Use this project's dotbrain-pstack mode to implement the approved API change.
Preserve the existing acceptance criteria and record actual checks and pending work.
```

The mode owns execution and recovery procedures. Core-only projects can use
another workflow with the same context and graph operations. No skill invocation
alone authorizes publication, messaging, merge or release.
