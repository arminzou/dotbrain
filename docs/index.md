---
layout: home
title: Dotbrain
titleTemplate: Private project context for coding agents

hero:
  name: Dotbrain
  text: Private context for coding agents
  tagline: Give each coding agent your project's decisions, vocabulary, and issues. Keep that context versioned and outside your code repo.
  image:
    light:
      src: /assets/mark-light-512.png
      width: 512
      height: 512
      fetchpriority: high
    dark:
      src: /assets/mark-dark-512.png
      width: 512
      height: 512
      fetchpriority: high
    alt: Dotbrain connected brain mark with a teal dot
  actions:
    - theme: brand
      text: Get started
      link: /getting-started
    - theme: alt
      text: Why Dotbrain?
      link: /why-dotbrain
    - theme: alt
      text: View on GitHub
      link: https://github.com/arminzou/dotbrain
---

<main class="home" aria-label="Dotbrain overview">

<section class="split">
<div>

## The repo stays clean

Each project's Brain and issue tracker live under `~/dotbrain/`. Gitignored links and generated runtime files connect the code repo to that private home, so agents load the context at session start and private material stays out of commits.

</div>
<div>

```mermaid
treeView-beta
  accTitle: A Brainspace and the code repo that links to it
  brainspaces/my-project/
    .brain/
      CONTEXT.md ## domain vocabulary
      adr/ ## architecture decisions
      designs/ ## design docs
      docs/ ## derived reference
    .beads/ ## issue tracker
  repos/my-project/
    .brain ## link to the Brainspace's .brain/
    .beads ## link to the Brainspace's .beads/
```

</div>
</section>

<section>

## Context that carries work forward

The Brain keeps project knowledge, the design captures current intent, and Beads tracks the issues. Focused skills connect them throughout the work.

<ol class="workflow" role="list">
<li>
<h3>Load the context</h3>
<p>Start from the project's vocabulary and decisions. Surface constraints and open questions before changing code.</p>
</li>
<li>
<h3>Settle the design</h3>
<p>Record the approach, unknowns, and success criteria in a living design. Turn it into scoped issues.</p>
</li>
<li>
<h3>Work the issues</h3>
<p>Implement and check each change. Feed discoveries back into the design and affected issues.</p>
</li>
<li>
<h3>Review and learn</h3>
<p>Review the result, record the evidence, and keep useful decisions in the Brain for the next session.</p>
</li>
</ol>

For example, an unexpected API constraint becomes a design question before a workaround. Once settled, the design and issues carry that decision forward. [Explore the skills](./skills).

</section>

<section>

## Wire a project in four steps {#wire-a-project-in-three-steps}

<ol class="steps" role="list">
<li>
<h3>Install the plugin</h3>
<p>In Claude Code, send these as two separate prompts. For Codex, follow the <a href="./getting-started#_1-install-the-plugin">installation guide</a>.</p>

```text
/plugin marketplace add arminzou/dotbrain
```

```text
/plugin install dotbrain@dotbrain
```

</li>
<li>
<h3>Get the CLI</h3>
<p>Invoke <code>wire-brain</code> in your coding agent. It installs the CLI and prerequisites if needed, then wires the repo. For manual setup, follow the <a href="./getting-started#_2-get-the-cli">CLI installation guide</a>.</p>

</li>
<li>
<h3>Wire a repo</h3>
<p>If you installed the CLI manually, create or repair the project's Brainspace and link it into the repo.</p>

```bash
dotbrain wire --repo ~/repos/my-app
```

</li>
<li>
<h3>Check the wiring</h3>
<p>A read-only health check. Then start a fresh agent session in the repo.</p>

```bash
cd ~/repos/my-app
dotbrain doctor
```

</li>
</ol>

</section>

<section>

## Read the docs

<div class="map">
<div>
<h3>Guide</h3>
<a href="./getting-started"><strong>Getting started</strong><span>Install, wire a repo, and verify the result.</span></a>
<a href="./prompts"><strong>Example prompts</strong><span>What to ask your agent for each common job.</span></a>
<a href="./architecture"><strong>Architecture</strong><span>Brainspaces, the Brain and execution split, the public/private boundary.</span></a>
<a href="./workflow"><strong>The workflow</strong><span>From first idea to closed design, one skill per step.</span></a>
<a href="./agent-team"><strong>Agent team</strong><span>Direct the work or hand it off, with one worker or several.</span></a>
<a href="./wiring"><strong>Wiring</strong><span>What gets linked, and when to wire, refresh, or unwire.</span></a>
<a href="./session-context"><strong>Session context</strong><span>What the agent knows when a session starts.</span></a>
<a href="./beads-backend"><strong>Beads backend</strong><span>Embedded and server modes for the issue tracker.</span></a>
<a href="./brain-site"><strong>Brain site</strong><span>Browse a Brain as a private local site.</span></a>
</div>
<div>
<h3>Reference</h3>
<a href="./cli-reference"><strong>CLI reference</strong><span>Every dotbrain command and option.</span></a>
<a href="./configuration"><strong>Configuration</strong><span>Annotated config.yaml and project.yaml.</span></a>
<a href="./skills"><strong>Skills</strong><span>The Brain-coupled skills the plugin ships.</span></a>
<a href="./glossary"><strong>Glossary</strong><span>The vocabulary of the dotbrain model.</span></a>
<a href="./troubleshooting"><strong>Troubleshooting &amp; FAQ</strong><span>Fixes for common setup and wiring problems.</span></a>
</div>
</div>

</section>

</main>
