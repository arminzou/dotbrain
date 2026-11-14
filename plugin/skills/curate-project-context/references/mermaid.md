# Mermaid diagrams

Read this before drawing a diagram in project documentation rendered with Mermaid.
Diagrams are fenced `mermaid` blocks;
the official [syntax reference](https://mermaid.js.org/intro/syntax-reference.html) holds the full
grammar for each type.

## Check the renderer

Check the project's Mermaid integration and version before choosing a diagram type or styling.
Prefer the theme's colours and fonts; per-diagram styling can break dark mode.
Sizing, scrolling, search indexing, and parse-error handling depend on the renderer.
A passing documentation build may not catch a diagram that fails in the browser, so open every
changed diagram in light and dark themes.

## Every diagram

- Start with `accTitle: <what the diagram shows>`. It is the diagram's accessible name.
- Use short ids and put the words in a quoted label: `api["Orders.Api"]`. Quote any
  label with spaces or punctuation.
- Name the key steps in the surrounding prose too, so they remain searchable and accessible.
- A trace whose steps are whole sentences reads better as a numbered list or a `text` block.

## Labels

One label style across every diagram, so readers learn it once:

- **Two lines: a bold name, then what it holds or does.** Write it as a markdown string, a quoted
  label wrapped in backticks:

  ```text
  plugin["`**Plugin**
    skills, convention, hook`"]
  ```

- **One line stays plain.** Bold only the first line of a two-line label; when everything is bold,
  nothing stands out.
- **Paths and file names are italic:** `*.brain/*`, `*~/dotbrain*`, `*AGENTS.md*`; on a bold line,
  `***.brain/***`. Backticks cannot appear inside a markdown string, so a path cannot be code.
  Sequence diagrams do not format text; paths stay plain there.
- **Arrow labels are plain verb phrases:** `reads and writes`, `wires`, `records decisions`.
- **Join phrases with words, commas, or a line break**, never a separator such as `·` or `|`.
- **An action is an arrow, not a note.** In a sequence diagram, the agent reading a file is a
  message to that file's participant; keep notes for commentary.

## Pick the type

| The reader needs to see | Type |
|---|---|
| A branch, a fan-in, shared steps, or what travels along an arrow | `flowchart` |
| A request passing between participants: browser, API, identity provider | `sequenceDiagram` |
| A lifecycle: a revision, a delivery, a message's settlement | `stateDiagram-v2` |
| A folder layout: what lives where | `treeView-beta` |

## Flowcharts

```mermaid
flowchart LR
  accTitle: Settlement decision
  outcome["Processing outcome"]
  outcome -->|accepted or duplicate| complete[Complete]
  outcome -->|malformed or rejected| deadLetter[Dead-letter]
```

Mermaid keeps the direction you write, so choose it for the page's content width.
Use `LR` for fans and chains of up to five short
steps, and `TB` for longer chains, long labels, or graphs. A diagram that is too wide as `LR` usually
fits as `TB` with `direction LR` inside each subgraph, one row per group.

Use the renderer's default arrow styling. Write a branch or a merge as another
line that reuses an id. Label an arrow with `-->|label|`.

## Sequence diagrams

```mermaid
sequenceDiagram
  accTitle: API key check
  participant Client as Automation client
  participant Api as API
  participant Db as Database
  Client->>Api: Request with API key header
  Api->>Db: Find the active key
  Db-->>Api: Stored secret hash
  Note over Api,Db: Hash the secret and compare in fixed time.
  Api-->>Client: Response
```

- Keep participant names to a word or two. Participant boxes narrow to fit the column, and a long
  single word breaks mid-word: put detail such as `MessageQueueProcessor` in a message instead.
- Check that all participants fit the page's content width or can scroll.
- Keep messages short and let them wrap on their own; leave out `<br/>`.
- A note over one participant is narrow. Span two for longer text: `Note over Api,Db: ...`.
- Put exact wire formats, such as headers and query strings, in an `http` block above the diagram
  rather than in a message.
- Use `->>` for a request and `-->>` for a response.

## State diagrams

```mermaid
stateDiagram-v2
  accTitle: Revision lifecycle
  [*] --> Provisioning
  Provisioning --> Active: healthy
  Provisioning --> Failed: unhealthy
  Active --> Inactive: deactivated
```

`[*]` marks the start; `State --> Other: event` labels a transition.

## Tree views

```mermaid
treeView-beta
  accTitle: Where configuration lives
  ~/dotbrain/
    config.yaml ## machine defaults
    brainspaces/
      my-app/
        .brain/
          project.yaml ## one project
```

- Use a tree view for folder layouts when the installed Mermaid version supports it.
- Indentation is the hierarchy. End a folder with `/`; it is drawn bold with a folder icon.
- `## text` after a name is its description. Keep descriptions short; they line up in one column
  after the longest name, so one long name pushes them all right.
- Keep roots short (`repos/my-app/`), and give the full location in the prose.
- A symlink is a plain entry whose description names its target: `.brain ## link to .brain/`.
- Icons, colours, and root presentation depend on the renderer. The label rules above do not
  apply: every entry is a path, so none is italic.

## Pitfalls

| Avoid | Use instead | Why |
|---|---|---|
| `end` as a flowchart id | `finish["End"]` | `end` is a keyword; the diagram fails to parse |
| `a[Worker (Processor)]` | `a["Worker (Processor)"]` | Parentheses, brackets, and braces end an unquoted label |
| Styling directives that override the theme | Structure with theme defaults | Colours and fonts must work in both themes |
| Trusting a passing build | Opening the page | Parse errors appear only in the browser |
| `` `code` `` inside a markdown-string label | `*italic*` | Backticks end the markdown string; the diagram fails to parse |
| A step list with no branches as a diagram | A numbered list | A straight chain of boxes adds height, not meaning |
