# Publishing lessons and references

A Brain site renders `learning/lessons/` and `learning/reference/` under Learn. This guide adds the
site's syntax and checks to the `teach-me` skill's lesson format, and it wins where the two differ.

## Where files go

- **Lesson:** `lessons/NNNN-<dash-case-name>.md`, taking the next number in the workspace. The
  number orders lessons within their topic everywhere Learn lists them: the sidebar, the home
  page's Learn overview, and previous/next links. "3 of 3" is the lesson's place among the lessons
  sharing its topic.
- **Reference:** `reference/<dash-case-name>.md`. References appear, sorted by title, in their
  topic's folded References subgroup.

A file name is the page's URL. Append rather than renumber; when the user does agree to reorder,
renumber the files and update every link to them.

## Frontmatter

Every lesson and reference carries exactly these three fields:

```yaml
---
title: Secret storage
description: An operator lesson on where the service keeps its secrets and who can read them.
topic: Operations
---
```

- `title` names the page in the sidebar and the Learn overview. Name the subject in a few words
  (Secret storage, Service identities) so the list can be skimmed; the Your win box says what the
  reader will be able to do. Give a reference a distinct title from its lesson, naming the subject
  and the kind of lookup (Secret access map, Identity roles).
- `description` is one sentence, shown under the lesson's title in the home page's
  `<LearnOverview />`.
- `topic` must match a `### ` heading under `## Topics` in `MISSION.md` exactly, or the build fails.
  That failure is deliberate: it keeps a page from silently dropping out of Learn.

The folder decides whether a page is a lesson or a reference; there is no kind field. Leave out a
date field too: each page shows its last-updated date from its latest Brain commit.

## Lesson shape

A lesson is short and completable in one sitting, gives one tangible win, and ties to its topic's
section of the mission. In order:

1. `# Title`, repeating the frontmatter title; the page has no automatic heading.
2. A `::: info Your win` box stating the win.
3. A `::: info Code basis` box when claims depend on code, naming the commit with a permalink.
4. `##` sections for the teaching; `###` for sub-parts that show in the page outline.
5. Retrieval practice, then the primary source (the highest-trust resource for the skill), a link to
   its reference, and a reminder to ask the agent follow-up questions.

A reference is the compressed essence of one or more lessons, for scanning and printing: decision
tables, flows, command cheat sheets, code snippets. It links back to its lesson.

## Markdown first, HTML only where Markdown cannot

Pages are Markdown that VitePress compiles into Vue components. Reach for plain Markdown and
VitePress's own extensions first; they need no styling and carry none of the HTML pitfalls below.
The two HTML patterns in the table have no native equivalent and are styled by the dotbrain
default theme. A Brain that adds its own class styles it in `.brain/site/theme/style.css`. For a need the
table does not cover, check [vitepress.md](./vitepress.md) for a native feature before writing HTML.

| Need | Write |
|---|---|
| A note, rule, or warning | `::: tip Decision rule` … `:::` (also `info`, `warning`, `danger`) |
| Code | A fenced block naming its language: `csharp`, `bash`, `powershell`, `json` |
| A flow, branch, sequence, or state diagram | A fenced `mermaid` block (below) |
| An annotated sketch Mermaid cannot shape, such as a request with its headers | A fenced `text` block |
| A table | A Markdown table; it scrolls on narrow screens by itself |
| Side-by-side comparison | One `###` subsection per item |
| A retrieval question | `::: details Question?` then the answer, leading with its **short answer**, then `:::` |
| Terms with definitions | `<dl><dt>Term</dt><dd>Definition</dd></dl>` |
| An automatically checked drill | A `<script setup>` block plus a `practice-form` (below) |

Diagrams follow [mermaid.md](./mermaid.md): which type to pick, how the site sizes and styles
them, and the syntax pitfalls.

A retrieval question, with Markdown in both the question and the answer:

```md
::: details JSON omits a required `name`. Which model should admit that possibility?
**The HTTP request model**, and possibly the command when the Application handler owns validation.
:::
```

Three rules come from every page being a Vue template:

- Keep an HTML block free of blank lines. A blank line ends the block, and an indented line after it
  becomes a code block that shows the raw markup as text.
- Put `{{` in code, or wrap the text in `v-pre` (`<span v-pre>{{ userId }}</span>`, or a
  `::: v-pre` container around a paragraph). Anywhere else Vue evaluates it as a template
  expression and the text silently disappears; the build still passes, so read the rendered page.
- Write a literal `<` in prose as `&lt;` or inside backticks; otherwise it is read as a tag and the
  build fails.

A drill keeps its logic in the page. Every answer takes the same format so the form gives no clues:

```md
<script setup>
import { ref } from 'vue'
const answer = ref('')
const correct = ref(null)
const check = () => { correct.value = answer.value.trim().toLowerCase() === 'status' }
</script>

<div class="practice-form">
  <label for="answer">Member name</label>
  <input id="answer" v-model="answer" autocomplete="off" aria-describedby="feedback" @keydown.enter="check">
  <button type="button" @click="check">Check</button>
  <p id="feedback" aria-live="polite" :class="{ ok: correct === true, no: correct === false }">
    <template v-if="correct === true">Correct: status carries the HTTP code.</template>
    <template v-else-if="correct === false">Try again: it repeats the HTTP status code.</template>
  </p>
</div>
```

## Links

| Target | Link |
|---|---|
| Another lesson or reference | Relative to the file: `../reference/problem-details.md` |
| Repository code | A permalink at the grounding commit on the public remote |
| A public project guide | Its published documentation-site URL |
| An external source | Its canonical URL |

Relative paths into the repository do not resolve from the Brain, and the build fails on any dead
internal link.

## New topics

After the user confirms a topic, add its `### ` section under `## Topics` in `MISSION.md` and its
heading in `RESOURCES.md`, as the lesson format says. Learn's sidebar and the home page's
`<LearnOverview />` pick it up from its first page. Any hand-written cards on `docs/index.md` are
the Brain's own: add one for the topic if the home page has them.

## Check

Run `dotbrain site build`. It passes when every page compiles, every lesson and reference names a
mission topic, every nav link resolves, and every internal link resolves. Preview with
`dotbrain site dev`, which serves on `127.0.0.1`.

When the Brain has no `.brain/site/`, it has no site: write the pages to this format anyway, skip
the build, and tell the user. Committing the Brain, and anything outward,
waits for the user's go-ahead.
