---
layout: home
title: Dotbrain
titleTemplate: 为 Coding Agent 提供私有的项目上下文

homeHero:
  title: 你项目的第二大脑。
  private: 只属于你。
  shared: 与你的 Agent 共享。
  tagline: 你的思考、skills 和 subagents。一处存放，接入每个仓库。
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/getting-started
    - theme: alt
      text: 为什么用 Dotbrain？
      link: /zh/why-dotbrain
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/arminzou/dotbrain
  worksWith: 支持的 Agent
  repo: 代码仓库 · 公开
  home: 私有目录 · ~/dotbrain
  chips:
    thinking: 思考
    skills: skills
    subagents: subagents

skillSpotlight:
  tabsLabel: 查看某个仓库使用的 skills
  linked: skills 链接自
  loads: 这个仓库里的每个 Agent 都加载这些 skills
  legend: [共用, 后端, 前端, 基础设施]

workLoop:
  core: 项目记忆
  stages: [加载上下文, 敲定设计, 处理任务, 审阅与沉淀]
  epic: 结账 v1
  frontier: 可开工
  blocks: 阻塞
  legend: [可开工, 进行中, 被阻塞, 已完成]
  issues: [新建订单表, 配置支付, 订单 API, 支付 Webhook, 结账页面]
---

<main class="home" aria-label="Dotbrain 概览">

<section class="split">
<div>

## 代码仓库保持干净

每个项目的 Brain 和任务跟踪都放在 `~/dotbrain/` 下。代码仓库通过被 gitignore 的链接和生成的 runtime 文件连到这个私有目录。Agent 在会话开始时加载上下文，私有内容不会进入提交。

</div>
<div>

<div class="tree-panel">
<div class="tp private">
<div class="tp-cap"><i class="tp-lock"></i>~/dotbrain/brainspaces/my-app</div>
<div class="tp-row dir">.brain/<span class="tp-note"></span></div>
<div class="tp-row dir in">adr/<span class="tp-note">架构决策</span></div>
<div class="tp-row dir in">designs/<span class="tp-note">设计文档</span></div>
<div class="tp-row dir in">docs/<span class="tp-note">参考文档</span></div>
<div class="tp-row file in">AGENTS.md<span class="tp-note">私有规则</span></div>
<div class="tp-row file in">CONTEXT.md<span class="tp-note">领域术语</span></div>
<div class="tp-row file in">DOTBRAIN.md<span class="tp-note">共享的 Brain 规则</span></div>
<div class="tp-row file in">project.yaml<span class="tp-note">skills 与任务跟踪配置</span></div>
<div class="tp-row file in">RETRO.md<span class="tp-note">复盘经验</span></div>
<div class="tp-row dir">.beads/<span class="tp-note">任务跟踪</span></div>
</div>
<div class="tp">
<div class="tp-cap"><i class="tp-repo"></i>~/repos/my-app</div>
<div class="tp-row link">.brain<span class="tp-chip">仅本地</span></div>
<div class="tp-row link">.beads<span class="tp-chip">仅本地</span></div>
<div class="tp-row file">AGENTS.md<span class="tp-note">一行指引，会提交</span></div>
</div>
<p class="tp-foot"><code>.brain</code> 和 <code>.beads</code> 写在 <code>.git/info/exclude</code> 里，Git 不会看到它们。</p>
</div>

</div>
</section>

<section class="split">
<div>

## 仓库里的每个 Agent 都用同一套 skills {#every-agent-in-the-repo-gets-the-same-skills}

skills 只需在 `~/dotbrain/` 里写一次，再为每个项目选好它需要的那一套。无论在仓库里打开哪个 Agent，加载的都是同一套 skills；Claude Code 和 Codex 还会拿到项目的 subagents。skills 改一次，所有用到它的仓库都会跟着更新。[为项目选择 skills](./configuration#project-yaml)。

</div>
<div>

<SkillSpotlight />

</div>
</section>

<section>

## 用图规划，循环推进 {#plan-as-a-graph-work-in-a-loop}

敲定的设计会拆成 Beads 里的任务，并按阻塞关系连起来。Agent 接手可以开工的任务，完成后解开下一个。过程中学到的东西会回到 Brain，下一次会话从更靠前的地方开始。[查看工作流](./workflow)。

<WorkLoop />

</section>

<section>

## 三步连接一个项目 {#wire-a-project-in-three-steps}

<ol class="steps" role="list">
<li>
<h3>配置你的 Coding Agent</h3>
<p>Claude Code 和 Codex 每台机器只需安装一次插件，即可使用 skills 和会话 hook。</p>
<p>其他 runtime 通过 CLI 配置，见 <a href="./getting-started#hermes">Hermes</a>、<a href="./getting-started#opencode">OpenCode</a>、<a href="./getting-started#pi">Pi</a> 或 <a href="./getting-started#cursor">Cursor CLI</a>。</p>

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

<p class="note">在 Claude Code 中，两行要分两次发送。在 Codex 中，先在 <code>/hooks</code> 里信任一次 dotbrain 的 hook，再新开一个线程。</p>
</li>
<li>
<h3>让 Agent 连接仓库</h3>
<p><code>wire-brain</code> skill 会在缺少 CLI 时先安装它，再把仓库链接到它的 Brainspace。</p>

```text
Use wire-brain to wire this repo with Dotbrain.
```

<p class="note">想手动操作？请看 <a href="./getting-started#_2-get-the-cli">CLI 安装指南</a>。</p>
</li>
<li>
<h3>检查连接</h3>
<p>只读的健康检查。通过后，在仓库里新开一个 Agent 会话。</p>

```bash
cd ~/repos/my-app
dotbrain doctor
```

</li>
</ol>

<div class="cta">
<h2>给你的项目一个第二大脑。</h2>
<p>装一次，连接一个仓库，之后你在那里打开的每个 Agent 都从项目已有的认识出发。</p>
<div class="cta-actions"><a class="cta-btn brand" href="./getting-started">快速开始</a><a class="cta-btn" href="./workflow">查看工作流</a></div>
</div>

</section>

</main>
