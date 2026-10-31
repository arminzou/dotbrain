---
layout: home
title: Dotbrain
titleTemplate: Private project context for coding agents

homeHero:
  title: Your project's second brain.
  private: Private to you.
  shared: Shared with your agents.
  tagline: Your thinking, skills and subagents. One home, every repo.
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
  worksWith: Works with
  repo: Code repo · public
  home: Private home · ~/dotbrain
  chips:
    thinking: thinking
    skills: skills
    subagents: subagents

skillSpotlight:
  tabsLabel: Show the skills a repo uses
  linked: Skills linked from
  loads: Every agent in this repo loads these skills
  legend: [shared, backend, frontend, infra]

workLoop:
  core: project memory
  stages: [Load the context, Settle the design, Work the issues, Review and learn]
  epic: Checkout v1
  frontier: ready frontier
  blocks: blocks
  legend: [ready, in progress, blocked, done]
  issues: [Add orders table, Payments setup, Orders API, Payment webhooks, Checkout page]
---

<main class="home" aria-label="Dotbrain overview">

<section class="split">
<div>

## The repo stays clean

Each project's Brain and issue tracker live under `~/dotbrain/`. Gitignored links and generated runtime files connect the code repo to that private home, so agents load the context at session start and private material stays out of commits.

</div>
<div>

<div class="tree-panel">
<div class="tp private">
<div class="tp-cap"><i class="tp-lock"></i>~/dotbrain/brainspaces/my-app</div>
<div class="tp-row dir">.brain/<span class="tp-note"></span></div>
<div class="tp-row dir in">adr/<span class="tp-note">architecture decisions</span></div>
<div class="tp-row dir in">designs/<span class="tp-note">design docs</span></div>
<div class="tp-row dir in">docs/<span class="tp-note">reference docs</span></div>
<div class="tp-row file in">AGENTS.md<span class="tp-note">private rules</span></div>
<div class="tp-row file in">CONTEXT.md<span class="tp-note">domain vocabulary</span></div>
<div class="tp-row file in">DOTBRAIN.md<span class="tp-note">shared Brain rules</span></div>
<div class="tp-row file in">project.yaml<span class="tp-note">skills and tracker</span></div>
<div class="tp-row file in">RETRO.md<span class="tp-note">lessons learned</span></div>
<div class="tp-row dir">.beads/<span class="tp-note">issue tracker</span></div>
</div>
<div class="tp">
<div class="tp-cap"><i class="tp-repo"></i>~/repos/my-app</div>
<div class="tp-row link">.brain<span class="tp-chip">local only</span></div>
<div class="tp-row link">.beads<span class="tp-chip">local only</span></div>
<div class="tp-row file">AGENTS.md<span class="tp-note">one pointer line, committed</span></div>
</div>
<p class="tp-foot"><code>.brain</code> and <code>.beads</code> are listed in <code>.git/info/exclude</code>, so Git never sees them.</p>
</div>

</div>
</section>

<section class="split">
<div>

## Every agent in the repo gets the same skills

Write skills once in `~/dotbrain/` and give each project the set it needs. Whichever agent you open in that repo loads the same set, and Claude Code and Codex get the project's subagents too. Fix a skill once and every repo that uses it gets the fix. [Choose a project's skills](./configuration#project-yaml).

</div>
<div>

<SkillSpotlight />

</div>
</section>

<section>

## Plan as a graph. Work in a loop.

A settled design becomes issues in Beads, linked by what blocks what. Agents pick up whatever is ready, close it, and unblock the next. What they learn goes back into the Brain, so the next session starts further ahead. [See the workflow](./workflow).

<WorkLoop />

</section>

<section>

## Wire a project in three steps {#wire-a-project-in-three-steps}

<ol class="steps" role="list">
<li>
<h3>Set up your coding agent</h3>
<p>For Claude Code and Codex, install the plugin once per machine. It provides skills and session hooks.</p>
<p>For CLI-based setup, see <a href="./getting-started#hermes">Hermes</a>, <a href="./getting-started#opencode">OpenCode</a>, <a href="./getting-started#pi">Pi</a>, or <a href="./getting-started#cursor">Cursor CLI</a>.</p>

::: code-group

```text [Claude Code]
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

```bash [Codex]
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

:::

<p class="note">In Claude Code, send the two lines as separate prompts. In Codex, trust the dotbrain hooks once in <code>/hooks</code>, then start a new thread.</p>
</li>
<li>
<h3>Ask your agent to wire the repo</h3>
<p>The <code>wire-brain</code> skill installs the CLI if it is missing, then links the repo to its Brainspace.</p>

```text
Use wire-brain to wire this repo with Dotbrain.
```

<p class="note">Prefer to do it by hand? Follow the <a href="./getting-started#_2-get-the-cli">CLI guide</a>.</p>
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

<div class="cta">
<h2>Give your project a second brain.</h2>
<p>Install once, wire a repo, and every agent you open there starts from what the project already knows.</p>
<div class="cta-actions"><a class="cta-btn brand" href="./getting-started">Get started</a><a class="cta-btn" href="./workflow">See the workflow</a></div>
</div>

</section>

</main>
