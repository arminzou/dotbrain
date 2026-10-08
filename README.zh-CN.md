<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/lockup-horizontal-dark-1024.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/lockup-horizontal-light-1024.png">
    <img src="docs/public/assets/lockup-horizontal-light-1024.png" alt="Dotbrain" width="480">
  </picture>
</p>

# Dotbrain

[English](README.md) | 简体中文

[![PyPI](https://img.shields.io/pypi/v/dotbrain?style=flat&logo=pypi)](https://pypi.org/project/dotbrain/)
[![CI](https://img.shields.io/github/actions/workflow/status/arminzou/dotbrain/ci.yml?branch=main&style=flat&logo=github&label=CI)](https://github.com/arminzou/dotbrain/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/dotbrain?style=flat&logo=python)](https://pypi.org/project/dotbrain/)
[![License: MIT](https://img.shields.io/badge/license-MIT-117967?style=flat)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-read-117967?style=flat)](https://arminzou.github.io/dotbrain/zh/)

**为 Claude Code 和 Codex 提供私有的项目上下文。**

让每个 Coding Agent 都能读到项目的决策、术语和任务。这些上下文有版本记录，
但不放在代码仓库里。

[文档](https://arminzou.github.io/dotbrain/zh/) ·
[快速开始](https://arminzou.github.io/dotbrain/zh/getting-started) ·
[工作流程](https://arminzou.github.io/dotbrain/zh/workflow)

### 为什么做这个

我的项目通常先私下开发，之后才公开。代码可以公开，但那些还没想清楚的决策、路线图和
背后的考虑，得有个单独的地方放。以前它们散落在 Obsidian、被 gitignore 的笔记和 Agent
的记忆里，每开一个新会话，都要重新翻找上下文，把项目再解释一遍。我想让这些思考有版本
记录，两个 Agent 都能读到，并且和手头的工作关联起来。于是有了 Dotbrain。

## 适合你吗？

如果你经常在不同的 Agent、会话或 Git worktree 之间切换，又有值得长期保留的项目上下文，
Dotbrain 会很合适。它给这些上下文一个单独的家：可以审阅，用 Git 管理版本，和要公开的
代码分开。

如果在 `AGENTS.md` 或 `CLAUDE.md` 里写几条常驻指令就够用了，那就保持简单。
Dotbrain 是本地工具，不是托管的团队知识库。

## 快速开始

把插件装进你的 Coding Agent 即可，不需要克隆本仓库。

**Claude Code**：下面两行要分两次发送：

```text
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

**Codex：**

```bash
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

在 Codex 中打开 `/hooks`，信任 dotbrain 的 hook，然后新开一个 thread。
Windows 用户请先开启
[开发人员模式](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)
再连接项目，这样 Dotbrain 不需要管理员权限就能创建目录符号链接。

然后对 Agent 说：

```text
Use wire-brain to wire this repo with Dotbrain.
```

这个技能会按需安装与插件版本匹配的 CLI、`uv` 和 Beads，完成本机配置，再把仓库连接到
它的私有 Brainspace。用下面的命令检查结果：

```bash
dotbrain doctor
```

在连接好的仓库里新开一个 Agent 会话，就会加载项目的 Brain 上下文。
手动安装、备份、在第二台机器上配置以及故障排查，见
[快速开始](https://arminzou.github.io/dotbrain/zh/getting-started)。

### 更新

插件和 CLI 要一起更新。在 Claude Code 中运行 `/plugin`，从菜单里更新 dotbrain，
再运行 `/reload-plugins`。在 Codex 中运行：

```bash
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

然后升级 CLI，并同步本机和各个项目：

```bash
uv tool install dotbrain@latest
dotbrain bootstrap
dotbrain refresh --all
```

如果 CLI 是用 pipx 或 pip 装的，就用对应的工具升级。详见
[保持更新](https://arminzou.github.io/dotbrain/zh/getting-started#staying-current)。

## 工作原理

每个项目在私有的 dotbrain 主目录（默认 `~/dotbrain/`）下都有一个 **Brainspace**。
里面有 **Brain**（术语、决策和设计）和 **执行存储**（用
[Beads](https://github.com/gastownhall/beads) 跟踪的任务）。代码仓库通过被 gitignore 的
符号链接连到这个 Brainspace，私有文件本身不进代码仓库。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/how-it-works-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/how-it-works-light.svg">
  <img src="docs/public/assets/how-it-works-light.svg" alt="Claude Code 和 Codex 在代码仓库中工作，通过被 gitignore 的链接连到独立的私有 Brainspace，其中存放 Brain 和 Beads。" width="1000">
</picture>

会话开始时，插件的 hook 会自动加载项目上下文。技能在被调用时指导具体工作；连接项目时，
选定的技能和子 Agent 会放进仓库里的 Agent 工作区。技能和 Claude 子 Agent 是符号链接，
Codex 子 Agent 则是自动生成、被 gitignore 的 TOML 文件。
`dotbrain wire` 会根据 Git 元数据，把 worktree 连到同一个 Brainspace。

用 `dotbrain projects list` 查看已注册的项目。在已连接的 checkout 里，
`dotbrain refresh` 负责维护当前 checkout，`dotbrain unwire` 断开连接，但保留共享的
Brainspace。在其他目录下运行时，用 `--project <name>` 指定项目；`refresh --all`
维护所有已注册项目。本机全局资源不会自动同步，需要手动运行 `skills link --scope global`
或 `agents link --scope global`。

Brain 用 Git 管理版本，请备份到**私有**远程仓库。Beads 数据库不在 Git 里，
要备份或共享任务，需要单独配置 Dolt remote 或共享服务器。
详见[架构](https://arminzou.github.io/dotbrain/zh/architecture)、
[项目连接](https://arminzou.github.io/dotbrain/zh/wiring)和
[Beads 后端](https://arminzou.github.io/dotbrain/zh/beads-backend)。

## 工作闭环

每做完一件事，下一个会话都应该知道得更多。Dotbrain 内置的技能把工作从想法推进到实现，
再把过程中学到的东西写回项目上下文。

**从 Brain 出发 → 探索未知 → 敲定决策 → 写设计 → 处理并验证任务 → 审阅 →
把长期有效的决策写回 Brain。**

闭环发生在两个地方：

- **工作过程中：**新发现会反馈到当前的设计和相关任务里。比如意外碰到一个 API 限制，
  它就成了一个设计问题；定下处理方式后，先把决策记进设计和任务，再继续实现。
- **审阅之后：**结束设计时，记录验证证据，把有用的决策和术语留在 Brain 里。
  下一个计划开始时，这些知识已经在那儿了。

Brain 存长期知识，设计记录当前意图，Beads 记录执行状态。每次交接都落在文档或任务记录里，
换一个会话或 Agent 也能接着做，不用翻聊天记录拼凑上下文。

成功标准和最终审阅由你说了算。工作跨多个会话或还有悬而未决的问题时，走完整个闭环；
小改动只用需要的那几步就行。

操作示例见[工作流程](https://arminzou.github.io/dotbrain/zh/workflow)，
完整的技能列表见[技能](https://arminzou.github.io/dotbrain/zh/skills)。

## 开发

CLI 是一个用 [uv](https://docs.astral.sh/uv/) 管理的 Python 包。

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
uv sync
uv run dotbrain --help
uv run pytest
```

要以 editable 模式安装 CLI，运行 `./scripts/dev-install.sh`（Windows 上运行
`.\scripts\dev-install.ps1`），然后运行 `dotbrain bootstrap`。
内置技能的源码在 [`plugin/skills/`](plugin/skills/)。
命令和选项见 [CLI 参考](https://arminzou.github.io/dotbrain/zh/cli-reference)。

提交 bug 或 PR 前，请先看[贡献指南](CONTRIBUTING.md)。

本项目采用 [MIT 许可证](LICENSE)。
