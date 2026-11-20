# Choose your engineering workflow

Dotbrain preserves project understanding and durable work state. Its five core
skills provide wiring, context maintenance, repository requirements, and native
Beads operations. Your selected engineering workflow decides how to investigate,
plan, delegate, verify, recover, and deliver work under user and repository authority.
Dotbrain ships no workflow of its own and needs no adapter for yours.

Use `maintain-brain` to preserve useful project understanding and clean up obsolete
Brain material within the requested scope. Use `work-graph` for
tasks, dependencies, claims, and execution evidence. Ask `repo-rules` explicitly
to initialize repository requirements; its assessment alone adopts no policy.
Enforcement implementation belongs to your engineering workflow.

## Where a workflow's records go {#records}

The convention that the session-start hook delivers routes information needing
durable preservation, even when the workflow's own instructions name a file.
Session reasoning, temporary checklists, and disposable experiments may remain
temporary. A task may finish without creating a Brain record or Beads issue.

| Workflow output | Destination |
| --- | --- |
| Work needing durable continuation or coordination | Beads issues; keep existing tracked work current |
| Understanding later work needs that existing sources do not adequately retain | The matching Brain record |
| Code and public guidance | The code repository |

Honor explicit capture requests. Preserve useful experimental conclusions without
retaining every prototype; keep artifacts when reproduction, consequential evidence,
review, or continuation needs them. Resume tracked work from Beads and relevant
project sources. Engineering workflows choose planning and capture timing; ordinary
work does not require a Brain-wide cleanup or retrospective.

## Use a skill-based workflow {#skill-workflow}

Select the workflow's skills like any other skills. For example, to use
[pstack](https://github.com/backnotprop/pstack), add it to your skill library and
select its skill bundle for the current checkout's project:

```bash
dotbrain skills add https://github.com/backnotprop/pstack.git
dotbrain skills link pstack/skills
```

Then invoke the workflow by its own entry point, such as pstack's `poteto-mode`.
Dotbrain changes the workflow's version only through `dotbrain skills update`. Scope, acceptance criteria,
permissions, and delivery authority still come from the user and the repository.
See [skills](skills.md#external-repositories) for updating and removing it, and
[configuration](configuration.md#project-yaml) for the `skills:` key.
