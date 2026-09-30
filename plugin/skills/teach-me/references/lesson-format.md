# Lesson and reference format

The format for pages captured into `.brain/learning/`. It is plain Markdown and does not depend on
any site. When the workspace's `AGENTS.md` names a learning site, that site's publishing guide adds
its own syntax and checks on top of this format. Where the two conflict, the site's guide wins.

## Where files go

- **Lesson:** `lessons/NNNN-<dash-case-name>.md`, taking the next number in the workspace. Numbers
  run across the whole workspace, so a lesson's number orders it within its topic but is not its
  position there. "3 of 3" is the lesson's place among the lessons that share its topic.
- **Reference:** `reference/<dash-case-name>.md`.

The file name is the page's identity: links point at it, and a site uses it as the URL. Add new
pages instead of renumbering. If the user agrees to reorder, rename the files and update every link
to them.

## Frontmatter

Every lesson and reference has exactly these three fields:

```yaml
---
title: Key Vault
description: An operator lesson on Key Vault secrets, managed identity access, and rotation.
topic: Operations
---
```

- `title` names the subject in a few words so a list of pages can be skimmed. Give a reference a
  different title from its lesson, naming the subject and what kind of lookup it is.
- `description` is one sentence.
- `topic` must exactly match a `### ` heading under `## Topics` in `MISSION.md`.

The folder decides whether a page is a lesson or a reference; there is no kind field. Leave out
dates: the Brain's git history records them.

## Lesson shape

A lesson is short enough to finish in one sitting. It gives one tangible win and ties to its topic's
section of the mission. In order:

1. `# Title`, repeating the frontmatter title.
2. **Your win:** one or two sentences on what the reader will be able to do.
3. **Code basis**, when claims depend on code: the commit they were checked against, as a permalink
   on the public remote.
4. `##` sections for the teaching, with `###` for sub-parts.
5. Retrieval questions, each followed by its answer, which starts with a short answer.
6. The primary source (the most trusted resource for the skill), a link to the lesson's reference,
   and a reminder that the reader can ask the agent follow-up questions.

A reference is the compressed essence of one or more lessons, for scanning: decision tables, flows,
command cheat sheets, code snippets. It links back to its lesson.

## Links

| Target | Link |
|---|---|
| Another lesson or reference | Relative to the file: `../reference/key-vault-roles.md` |
| Repository code | A permalink at the grounding commit on the public remote |
| A public project guide | Its published URL |
| An external source | Its canonical URL |

Relative paths into the repository do not resolve from the Brain.

## New topics

After the user confirms a topic, add its `### ` section under `## Topics` in `MISSION.md`
([format](./mission-format.md)) and its heading in `RESOURCES.md`.
