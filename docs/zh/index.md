---
layout: home
title: Dotbrain
titleTemplate: 为 Coding Agent 提供私有的项目上下文

homeHero:
  title: 你项目的第二大脑。
  private: 只属于你。
  shared: 与你的 Agent 共享。
  tagline: 你的思考、技能和子 Agent。一处存放，接入每个仓库。
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
    skills: 技能
    subagents: 子 Agent

skillSpotlight:
  tabsLabel: 查看某个仓库使用的技能
  linked: 技能链接自
  loads: 这个仓库里的每个 Agent 都加载这些技能
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

每个项目的 Brain 和任务跟踪都放在 `~/dotbrain/` 下。代码仓库通过被 gitignore 的链接和生成的运行时文件连到这个私有目录。Agent 在会话开始时加载上下文，私有内容不会进入提交。

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

<section class="split">
<div>

## 仓库里的每个 Agent 都用同一套技能 {#every-agent-in-the-repo-gets-the-same-skills}

技能只需在 `~/dotbrain/` 里写一次，再为每个项目选好它需要的那一套。无论在仓库里打开哪个 Agent，加载的都是同一套技能；Claude Code 和 Codex 还会拿到项目的子 Agent。技能改一次，所有用到它的仓库都会跟着更新。[为项目选择技能](./configuration#project-yaml)。

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

## 四步连接一个项目 {#wire-a-project-in-three-steps}

<ol class="steps" role="list">
<li>
<h3>安装插件</h3>
<p>在 Claude Code 中，下面两行要分两次发送。Codex 用户请看<a href="./getting-started#_1-install-the-plugin">安装指南</a>。</p>

```text
/plugin marketplace add arminzou/dotbrain
```

```text
/plugin install dotbrain@dotbrain
```

</li>
<li>
<h3>安装 CLI</h3>
<p>在 Coding Agent 里调用 <code>wire-brain</code>。它会按需安装 CLI 和依赖，然后连接仓库。想手动安装，请看 <a href="./getting-started#_2-get-the-cli">CLI 安装指南</a>。</p>

</li>
<li>
<h3>连接仓库</h3>
<p>如果是手动安装的 CLI，用下面的命令创建或修复项目的 Brainspace，并把它链接到仓库。</p>

```bash
dotbrain wire --repo ~/repos/my-app
```

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

</section>

</main>
