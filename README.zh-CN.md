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

**为你的 Coding Agent 管理私有项目上下文。**

支持 Claude Code、Codex、Hermes、OpenCode、Pi 和 Cursor CLI。

Dotbrain 将管理 Dotfiles 的方式用在项目上：把工作笔记、计划、agent instructions 和选用的 Agent 资源
集中保存在私有目录中，再连接到你使用的各个 checkout。

这些上下文以本地文件保存，有独立的 Git 历史。Dotbrain CLI 负责将这个工作区连接到代码仓库，
内置的 workflow skills 则指导 Agent 使用这些上下文，并与你一起持续维护。

[https://github.com/user-attachments/assets/540e8945-b8bc-4fc1-ac05-c125bf768fa9](https://github.com/user-attachments/assets/021fc13a-db20-4549-8aab-b5240d289bde)

[文档](https://arminzou.github.io/dotbrain/zh/) ·
[快速开始](https://arminzou.github.io/dotbrain/zh/getting-started) ·
[工作流程](https://arminzou.github.io/dotbrain/zh/workflow)

### 为什么做 Dotbrain

Global agent instructions（如 `~/.codex/AGENTS.md` 或 `~/.claude/CLAUDE.md`）定义了我希望 Agent 平时如何做事。
Repo-level instructions（如仓库里的 `AGENTS.md` 或 `CLAUDE.md`）则约定了 Agent 在这个 repo 中该如何修改代码。
而我对某个项目的思考、工作笔记和计划，也需要一个私有的存放空间。

以前，这些内容散落在 Obsidian、被 Git 忽略的笔记和 Agent 的记忆里。每次开始新会话，
都要花时间重新整理上下文；换一个 checkout，还得重新配置常用的 skills 和 subagents。
所以我做了 Dotbrain，把这些内容集中管理，让每个 checkout 都能接入同一个项目工作区。

关于 Dotbrain 的设计思路：[Dotfiles for Your Repo](https://x.com/i/article/2109385521214390273)。

## 适合你吗？

如果你希望累积的项目上下文、进行中的计划、personal agent instructions 和选用的 skills，能在不同的 Agent、
会话和 worktree 之间持续使用，Dotbrain 可以为它们提供一个统一的私有工作区。

Dotbrain 可以与 Agent 自带的记忆系统及其他上下文工具配合使用。工作区由你掌控，
哪些结论写入仓库的共享文档、哪些整理成公开提案，都由你决定。

如果在 `AGENTS.md` 或 `CLAUDE.md` 中写几条长期适用的 instructions 就能满足需求，保持简单即可。

## 快速开始

根据你使用的 Coding Agent 选择安装方式：Claude Code 和 Codex 通过 marketplace 安装插件，
Hermes、OpenCode、Pi 和 Cursor CLI 通过 CLI 配置。无需克隆本仓库。

**Claude Code**：下面两条命令要分两次发送：

```text
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

**Codex：**

```bash
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

在 Codex 里打开 `/hooks`，信任 dotbrain 的 hook，然后新开一个 thread。
[Hermes](https://arminzou.github.io/dotbrain/zh/getting-started#hermes)、
[OpenCode](https://arminzou.github.io/dotbrain/zh/getting-started#opencode)、
[Pi](https://arminzou.github.io/dotbrain/zh/getting-started#pi) 和
[Cursor](https://arminzou.github.io/dotbrain/zh/getting-started#cursor) 则通过 CLI 安装，具体步骤见各自的文档。
Windows 用户请先开启
[开发人员模式](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)
再连接项目，这样 Dotbrain 不用管理员权限也能创建目录符号链接。

接着告诉 Agent：

```text
Use wire-brain to wire this repo with Dotbrain.
```

`wire-brain` skill 会按需安装版本匹配的 CLI、`uv` 和 Beads，配置本机环境，并将仓库连接到它的私有
Brainspace。完成后，运行以下命令检查配置：

```bash
dotbrain doctor
```

在已连接的仓库中新开一个 Agent 会话，Dotbrain 会自动加载共享约定，让 Agent 知道
项目上下文存放在哪里、如何使用。
手动安装、备份、换机器配置和故障排查，见
[快速开始](https://arminzou.github.io/dotbrain/zh/getting-started)。

### 更新

使用 Claude Code 或 Codex 时，插件和 CLI 需要一起更新。在 Claude Code 中运行 `/plugin`，从菜单中更新 dotbrain，
再运行 `/reload-plugins`。Codex 则运行：

```bash
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

然后升级 CLI，更新本机和各项目的配置与资源：

```bash
uv tool install dotbrain@latest
dotbrain bootstrap
dotbrain refresh --all
```

如果 CLI 是通过 pipx 或 pip 安装的，请使用对应工具升级。详见
[保持更新](https://arminzou.github.io/dotbrain/zh/getting-started#staying-current)。
使用 Hermes、OpenCode、Pi 或 Cursor CLI 时，升级 CLI 后运行 `dotbrain bootstrap` 更新对应的集成，
具体说明见上方各 runtime 的安装文档。

## 工作原理

每个项目在私有的 dotbrain 主目录（默认为 `~/dotbrain/`）下都有一个 **Brainspace**，
其中包含 **Brain**（`.brain/`，用本地 Markdown 文件记录项目规则、术语、决策和设计）
和 **execution store**（`.beads/`，保存由 [Beads](https://github.com/gastownhall/beads) 跟踪的任务）。
checkout 通过符号链接访问它们。这些链接被 Git 忽略，实际文件和历史记录也保存在代码仓库之外。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/how-it-works-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/how-it-works-light.png">
  <img src="docs/public/assets/how-it-works-light.png" alt="Claude Code 和 Codex 在代码仓库中工作，通过被 Git 忽略的链接访问独立的私有 Brainspace，其中存放 Brain 和 Beads。" width="1000">
</picture>

图中以 Claude Code 和 Codex 为例，所有受支持的 runtime 都使用同样的 Brainspace 结构。

连接项目时，Dotbrain 会将选用的 skills 配置到各 runtime 的项目 skills 目录中。
Native subagents 支持 Claude Code 和 Codex：Claude 资源在 `.claude/` 下，Codex skills 在
`.agents/skills/` 下，Codex subagents 在 `.codex/agents/` 下。Codex 配置仍留在 `.codex/` 下。
Skills 和 Claude subagents 使用符号链接，Codex subagents 则使用自动生成、被 Git 忽略的
TOML 文件。连接 Git worktree 时，会复用主 checkout 已有的 Brainspace，
两边共用同一份项目知识和任务记录。
Hermes、OpenCode、Pi 和 Cursor CLI 支持 skills 和会话集成，但 Dotbrain 不会为它们配置 native subagents。

会话开始时，各 runtime 的集成只加载共享约定 `DOTBRAIN.md`。不同 runtime 的上下文加载和同步方式，
见[运行时说明](https://arminzou.github.io/dotbrain/zh/session-context#runtime-notes)。
公开的 `AGENTS.md` 会要求 Agent
在修改或审阅代码前，读取仓库根目录下由 Git 跟踪的 `RULES.md`；这些规则在没有 Brain 的环境中也适用。
Lead 或独立完成任务的 Agent 会按任务检索私有复盘记录，并将相关发现随任务说明交给 worker 和 reviewer，
无需在会话启动时加载整份复盘笔记。

新建 Brain 时会生成私有的 `AGENTS.md`，用于保存少量个人偏好和项目私有规则，
`CLAUDE.md` 则是指向它的符号链接。Agent 会在开始实质工作前读取这些内容，而非在会话启动时自动加载。
`wire` 和 `refresh` 会保留已有内容，以及指向其他上下文文档的引用。仓库的公共要求写在公开的 `RULES.md` 中，个人偏好则保留在私有空间。
加载顺序见[会话上下文](https://arminzou.github.io/dotbrain/zh/session-context)。

`dotbrain projects list` 可以列出已注册的项目。在已连接的 checkout 里，
`dotbrain refresh` 更新当前 checkout 的配置与资源，`dotbrain unwire` 断开连接，但保留共享的
Brainspace。在其他目录中，可用 `--project <name>` 指定项目；`refresh --all`
会处理所有已注册的项目。全局资源需要单独更新，运行 `skills link --scope global` 或
`subagents link --scope global`。

Brain 使用 Git 管理版本，请将它备份到**私有**远程仓库。Beads 数据库不纳入 Git，
备份或共享任务需要另行配置 Dolt remote 或共享服务器。
详见[架构](https://arminzou.github.io/dotbrain/zh/architecture)、
[项目连接](https://arminzou.github.io/dotbrain/zh/wiring)和
[Beads 后端](https://arminzou.github.io/dotbrain/zh/beads-backend)。

## 工作闭环

每完成一项工作，都应该为下一次会话留下有用的上下文。Dotbrain 内置的 skills 帮助你从想法推进到实现，
再将过程中获得的知识写回项目上下文。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/public/assets/workflow-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/public/assets/workflow-light.png">
  <img src="docs/public/assets/workflow-light.png" alt="工作流涵盖探索未知、确定决策、设计、任务拆分、执行、审阅和设计收尾。新发现更新到当前设计，长期有效的决策写回 Brain，为下一轮工作提供上下文。" width="880">
</picture>

闭环体现在两处：

- **工作过程中：** 新发现会更新到当前设计和受影响的任务中。例如，实现时遇到未预料的
  API 限制，就需要重新考虑相关设计。你做出决定后，先更新设计和任务记录，再继续实现。
- **你合并 PR 并要求设计收尾后：** 收尾时会记录验证证据，并将值得保留的决策和术语整理到 Brain 中，
  供后续工作直接使用。

Brain 保存长期知识，设计说明当前要做什么，Beads 跟踪执行状态。每次交接都有文档或任务记录可查，
换一个会话或 Agent，也能继续推进。

成功标准、PR 批准、合并和发布由你决定。执行前，先确定可预见的设计选择，明确执行范围和权限。
完整且仍适用的授权可以继续使用，无需反复确认。Agent 完成检查、验收/UAT 和必要的审阅后，
会将 PR 标为 ready，并请求你审阅。

如果出现新的范围、权限或验收标准问题，Agent 会暂停受影响的工作，提供证据和建议，由你决定。
恢复执行时，既定的尝试次数或预算上限仍然有效。设计会保持 active 状态，直到你要求收尾；
PR 关闭但未合并不算交付。跨会话或仍有待解决问题的工作适合走完整流程，小改动则可以只用其中必要的步骤。

操作示例见[工作流程](https://arminzou.github.io/dotbrain/zh/workflow)，
完整的 skill 列表见 [Skills](https://arminzou.github.io/dotbrain/zh/skills)。

## 开发

CLI 是一个用 [uv](https://docs.astral.sh/uv/) 管理的 Python 包。

```bash
git clone https://github.com/arminzou/dotbrain.git
cd dotbrain
uv sync
uv run dotbrain --help
uv run pytest
```

如需以 editable 模式安装 CLI，运行 `./scripts/dev-install.sh`（Windows 上为
`.\scripts\dev-install.ps1`），再运行 `dotbrain bootstrap`。
内置 skills 的源码在 [`plugin/skills/`](plugin/skills/)。
命令和选项见 [CLI 参考](https://arminzou.github.io/dotbrain/zh/cli-reference)。

提交 bug 或 PR 前，请先阅读[贡献指南](CONTRIBUTING.md)。

本项目采用 [MIT 许可证](LICENSE)。
