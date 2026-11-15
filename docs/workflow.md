# Choose your engineering workflow

Dotbrain preserves project understanding and durable work state. Its five core
skills provide wiring, context maintenance, repository requirements, and native
Beads operations. Your selected engineering workflow decides how to investigate,
plan, delegate, verify, recover, and deliver work under user and repository authority.
Dotbrain ships no workflow of its own and needs no adapter for yours.

Use `maintain-brain` to capture vocabulary, accepted decisions, designs, verified
findings, and unresolved hypotheses with their evidence. Use `work-graph` for
tasks, dependencies, claims, and execution evidence. Ask `repo-rules` explicitly
to initialize repository requirements; its assessment alone adopts no policy.
Enforcement implementation belongs to your engineering workflow.

## Where a workflow's records go {#records}

The convention that the session-start hook delivers decides where any workflow's
records go, even when the workflow's own instructions name a file:

| Workflow output | Destination |
| --- | --- |
| Plans, task lists, progress, and handoff notes | Beads issues |
| Design reasoning, decision logs, and research | The matching Brain record |
| Code and public guidance | The code repository |

A later session resumes from `bd ready` and the Brain, not from transcripts or
files in the repository.

## Use a skill-based workflow {#skill-workflow}

Select the workflow's skills like any other skills. For example, to use
[pstack](https://github.com/backnotprop/pstack), clone it into your skill library
and select its skill bundle for a project:

```bash
git clone https://github.com/backnotprop/pstack.git ~/dotbrain/skills/pstack
```

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - pstack/skills
```

```bash
dotbrain skills link
```

Then invoke the workflow by its own entry point, such as pstack's `poteto-mode`.
Dotbrain does not install, pin, or update the workflow. Scope, acceptance criteria,
permissions, and delivery authority still come from the user and the repository.
See [skills](skills.md) for selection rules and [configuration](configuration.md#project-yaml)
for the `skills:` key.
