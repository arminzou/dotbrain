---
layout: home
title: Dotbrain
titleTemplate: 为 Coding Agent 提供私有的项目上下文

hero:
  name: Dotbrain
  text: 为 Coding Agent 提供私有上下文
  tagline: 让每个 Coding Agent 都能读到项目的决策、术语和任务。这些上下文有版本记录，但不放在代码仓库里。
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
    alt: Dotbrain 的标志：相连的大脑图形和一个青色圆点
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

<section>

## 让上下文推动工作向前

Brain 存项目知识，设计记录当前意图，Beads 跟踪任务。一组专注的技能在整个过程中把它们串起来。

<ol class="workflow" role="list">
<li>
<h3>加载上下文</h3>
<p>从项目的术语和决策出发，在改代码之前先找出约束和未解决的问题。</p>
</li>
<li>
<h3>敲定设计</h3>
<p>把方案、未知项和成功标准写进一份持续更新的设计，再拆成范围明确的任务。</p>
</li>
<li>
<h3>处理任务</h3>
<p>实现并检查每个改动，把新发现反馈到设计和相关任务里。</p>
</li>
<li>
<h3>审阅与沉淀</h3>
<p>审阅结果，记录证据，把有用的决策留在 Brain 里，留给下一个会话。</p>
</li>
</ol>

比如意外碰到一个 API 限制，它会先成为一个设计问题，而不是直接绕过去。定下来之后，设计和任务会把这个决策带下去。[了解这些技能](./skills)。

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

<section>

## 阅读文档

<div class="map">
<div>
<h3>指南</h3>
<a href="./getting-started"><strong>快速开始</strong><span>安装、连接仓库并验证结果。</span></a>
<a href="./prompts"><strong>示例提示词</strong><span>每类常见工作该怎么跟 Agent 说。</span></a>
<a href="./architecture"><strong>架构</strong><span>Brainspace、Brain 与执行的分离，以及公开/私有的边界。</span></a>
<a href="./workflow"><strong>工作流程</strong><span>从最初的想法到结束设计，每一步对应一个技能。</span></a>
<a href="./agent-team"><strong>Agent 团队</strong><span>由你指挥或交给 Agent，了解一个或多个 worker 怎样协作。</span></a>
<a href="./wiring"><strong>项目连接</strong><span>会链接哪些东西，什么时候该 wire、refresh 或 unwire。</span></a>
<a href="./session-context"><strong>会话上下文</strong><span>会话开始时 Agent 知道些什么。</span></a>
<a href="./beads-backend"><strong>Beads 后端</strong><span>任务跟踪的 embedded 模式和 server 模式。</span></a>
<a href="./brain-site"><strong>Brain 站点</strong><span>把 Brain 当作一个私有的本地网站来浏览。</span></a>
</div>
<div>
<h3>参考</h3>
<a href="./cli-reference"><strong>CLI 参考</strong><span>dotbrain 的所有命令和选项。</span></a>
<a href="./configuration"><strong>配置</strong><span>带注释的 config.yaml 和 project.yaml。</span></a>
<a href="./skills"><strong>技能</strong><span>插件自带的、与 Brain 配合的技能。</span></a>
<a href="./glossary"><strong>术语表</strong><span>dotbrain 模型中的术语。</span></a>
<a href="./troubleshooting"><strong>故障排查与常见问题</strong><span>常见安装和连接问题的解决办法。</span></a>
</div>
</div>

</section>

</main>
