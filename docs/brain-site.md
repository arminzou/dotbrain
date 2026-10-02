# Browse the Brain

A project's private knowledge is often easier to use as a website than as raw Markdown in a
coding editor. Brain Site provides formatted pages, search, navigation, and rendered diagrams
while keeping the material in the project's private Brain.

Use it to learn project topics with an agent, read personal runbooks, revisit decisions, and
look up sensitive project context. The site serves locally on `127.0.0.1`; Dotbrain does not publish it.

## Learn Project Topics with an Agent

Work with an agent using `teach-me` to learn the parts of the project that interest you. Keep
the Brain site open alongside the conversation: the agent explains, asks questions, and guides
practice while the site gives you a visual place to read lessons, follow diagrams, and consult
references.

The site provides a dedicated **Learn** experience. Its sidebar groups lessons and references
by the topics in your learning mission. The standard home page shows a Learn overview with topic
tiles and recent lessons, plus a Start learning link when lessons exist.

For example, choose a topic to discuss with your agent, open its lesson in the browser, and ask the agent
to walk you through it. Read the diagram, try the retrieval exercise, and discuss your answer
with the agent. The agent records demonstrated understanding and updates your learning path.
Learning records are also rendered as pages, so you can read what has been established and what
still needs practice; they are reachable through links and search, rather than the topic's lesson list.

The [learning workflow](learning.md) explains how topics, learning paths, records, and parked
concepts carry learning across sessions. Brain Site makes that material comfortable to explore
and use during the learning itself.

## Read Private Runbooks and Project Docs

Keep operational instructions and internal reference material in the Brain, where they can
include project context without becoming public repository documentation. The site renders
headings, tables, code blocks, links, and Mermaid diagrams for comfortable reading.

For example, a private deployment runbook can link to a recovery procedure and the design that
explains a constraint. Follow those links while working through the procedure without opening
and interpreting each Markdown source file in an editor.

## Search Across the Brain

The site renders Markdown across the Brain, including private docs, decisions, designs, and
learning material. Search helps you find a relevant page when you remember a term or a problem
but not its filename.

The sidebar provides a shorter route to pages you use often. It controls navigation rather than
which pages exist: a page left out is still reachable by links and search. Some files, including
symlinks and files with bracketed names, are skipped; see the
[configuration guide](brain-site-configuration.md#how-pages-map-to-urls) for the mapping rules.

## Navigate Decisions and Designs

Relative links connect docs to decisions and designs at their existing Brain paths. Decision
status and design lifecycle badges help you recognize which records are current and which
describe an earlier point in time.

## Set Up the Reading Experience

Follow [Brain Site configuration](brain-site-configuration.md) to create the site, serve it
locally, arrange the sidebar, and adjust its appearance. You can also ask the agent's `brain-site`
skill to help maintain it.

Markdown stays the authored source. Keep editing it in your usual tools and read the rendered
pages in the browser.
