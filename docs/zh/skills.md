# Skills

Dotbrain 内置了配合 Brain 使用的 workflow skills，相当于已连接项目的操作手册。它们涵盖连接、规划、执行、公开 issue 的分类处理和
Brain 维护。其中有几个借鉴并改编自 [mattpocock/skills](https://github.com/mattpocock/skills)。

[工作流程](workflow.md)展示了它们如何配合。

skills 的链接由你自己管理：

- 全局 skills 在 `~/dotbrain/config.yaml` 里选择
- 项目 skills 在 `brainspaces/<name>/.brain/project.yaml` 里选择

## 选择和同步 skills {#select-and-reconcile-skills}

Codex 项目 skills 链接到 `<checkout>/.agents/skills/`。配置和 subagents 仍放在 `.codex/` 下；全局 skills 继续
使用 `~/.codex/skills/` 和配置的 profile 主目录。Claude Code 和其他 runtime 的目标位置不变。

`wire`、`refresh` 和 `skills link` 会根据链接目标判断归属，迁移 `.codex/skills/` 下 dotbrain 自己的旧链接。
选中的旧链接会在新链接分发成功后移除，不再选中的自有链接会被清理。无法确认归属的文件、目录和链接都会保留并
报告；新位置发生冲突时，旧链接也会保留。处理冲突后重新运行即可。每个分发的资源都单独被 gitignore，
`unwire` 会清理新旧位置的自有链接。这些检查只能证明文件系统状态，runtime 是否发现和调用了 skills 需要另行验证。

两种范围都可以选单个 skill，也可以选一个 skill bundle 目录：

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/config.yaml
version: 4
profiles:
  claude-code: [~/.claude-work]
skills:
  - another-collection
```

全局链接使用各 runtime 的默认主目录。Claude Code 和 Codex 还可通过 `profiles` 添加额外主目录，skills 会
链接到每个主目录下的 `skills/`，不存在的主目录会跳过。请填写 runtime 主目录，不要填写项目 checkout
内的目录。详见[配置](configuration.md#global-skills)。

包含 `SKILL.md` 的目录只选中它自己，即使它下面还有子 skill。否则，dotbrain 会递归查找所有包含 `SKILL.md` 的
子目录，`node_modules` 除外。重复选中同一来源会去重。不同来源映射到同一个目标名（包括在不区分大小写的文件系统
上只有大小写不同）时，会在改动目标之前失败。路径不存在、不是目录或 skill bundle 为空时，也会失败并给出可操作的提示。

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

在选中的 skill bundle 里增删 skills，下次同步时就会生效，声明本身不变。被移除的、dotbrain 自己的链接会被清理，
其他来源的条目会保留。`projects show`、skills 目录和 doctor 都使用同样的展开结果。

## 核心工作流程 {#core-workflow}

从连接项目、明确决策、设计和拆分任务，到执行、审阅、收尾，再到整理项目上下文。
`write-agent-docs` 为这些环节提供写作规范，Agent 仍可按需自动调用。

### 配置 {#setup}

- **`wire-brain`**：创建或修复仓库与其私有 Brain 之间的 Brainspace 连接，包括恢复链接出来的 worktree 的
  `.brain` 和 `.beads`。第一次使用时，如果缺少 `dotbrain` CLI 会自动安装。

### 规划 {#planning}

- **`to-design`**：把一项多步骤的工作写成一份持续更新的 active 设计文档，存进 Brain，并创建一个 epic bead。
  适合在拆分之前需要明确设计、或需要一个地方跟踪未知项的工作。
- **`to-issues`**：把设计文档拆成可以独立处理的 bead 任务，带验收标准和依赖，并用
  `--spec-id design:<slug>` 把每个 bead 关联回设计。
- **`grill-decisions`**：对照项目的术语和决策对计划做压力测试，再把长期有效的结论写进 `CONTEXT.md` 和 `adr/`。
- **`find-unknowns`**：在确定设计之前，找出陌生领域里的盲点和隐含假设。
- **`close-design`**：把设计文档推进到终态；认定已交付前核实 PR 合并证据，记录结果，
  将值得保留的决策和术语整理到 `adr/` 和 `CONTEXT.md`，关闭 epic。

### 执行 {#execution}

- **`manage-work-graph`**：在私有工作图里创建、查看、认领、拆分、更新和关闭工作项
- **`run-execution`**：完成一个工作项或一批固定的工作项：分派 worker，让每个改动都经过独立审阅，合并，检查，
  在限度内修复，必要时上报或恢复
- **`iterate-design`**：用 Agent 原生的循环模式推进一份 active 设计文档：规划、实现、验证、反思，通过一个
  draft PR 交付，完成后转为 ready 等你审阅，在成功或阻塞时停下

### 审阅与整理 {#review-and-curate}

- **`review-gate`**：执行 review（代码、简化或交付准备情况），并将结论和问题处理结果记录在任务中；必要证据对应待验收的 commit、
  各条发现处理完毕后，lead 可在 PR 合并前关闭已通过的审阅。PR 批准、合并和发布仍由你决定
- **`curate-project-context`**：在公开项目和私有 Brain 中找出并修复过时、重复、放错位置、无法访问或泄露的上下文
- **`write-agent-docs`**：为公开项目文档、私有 Brain 内容、用户自己的 skills，以及 Agent 通过指针读到的指引
  提供写作规范

## 按名称调用的可选 skills {#optional-skills-invoked-by-name}

这些 skills 仍随插件提供。在 Claude Code 中用 `/dotbrain:<name>`，在 Codex 中用 `$<name>`。
`dotbrain` 和 `triage-public` 也可以直接用文字要求启动；其他 skills 只能按名称调用。

- **`dotbrain`**：操作约定本身。会话启动 hook 会自动注入它；在不运行 hook 的 runtime 里，直接要求或按名称调用都可以。
- **`run-retro`**：整理工作和审阅记录中的经验，或检查这些经验是否改善了后续行为。
  手动调用，也可由你配置定时任务运行。建议默认保留在私有 Brain 中；详见[复盘](#retrospectives)。
- **`triage-public`**：对公开任务跟踪里的条目分类，把准备好的工作提升到私有执行中
- **`review-architecture`**：审查代码库，寻找可以简化接口、将实现复杂度封装在模块内部的机会

### Brain 站点 {#brain-site}

- **`brain-site`**：手动调用，用 `dotbrain site` 创建、维护、构建或预览 Brain 的私有站点，
  包括侧边栏、主题和页面渲染检查

### 学习 {#learning}

学习路径、暂存的概念和会话之间的延续，请看[学习你的项目](learning.md)。

- **`teach-me`**：跨多个会话，根据 Brain 教你了解自己的项目：在对话中讲解，按一条以 `learn:` bead 跟踪的
  学习路径推进，记录你展示出的理解，并把认可的课程保存到 `.brain/learning/`

## subagents {#subagents}

除了 skills，dotbrain 还自带能读 Brain 的 subagents：`worker`、`reviewer`、`verifier` 和 `researcher`。见
[会话上下文](session-context.md#subagents)。

`config.yaml` 的 `subagents:` 选中的自定义 subagents 共用默认主目录和 `profiles:`，
分发到 Claude Code 和 Codex 各主目录下的 `agents/`。详见
[配置](configuration.md#global-subagents)。

## 安装 {#installing-them}

Claude Code 和 Codex 的 skills 随 marketplace 插件一起提供，每台机器上的每个 runtime 只需安装一次，无需按仓库重复安装。安装命令见[快速开始](getting-started.md)。
插件装在用户级别，所以它的 skills 在每个会话里都可用，包括还没连接的仓库。

Hermes 的 skills 来自 `dotbrain bootstrap --runtime hermes` 放进 Hermes 主目录的插件副本，
项目选中的 skills 来自已信任 checkout 里的 `.hermes/skills/`。只能手动调用的 skills 会出现在 Hermes 的列表里，
但模型加载不了，要你自己调用。详见[Hermes](getting-started.md#hermes)。

OpenCode 的 skills 来自 `dotbrain bootstrap --runtime opencode` 放进 OpenCode 配置目录的打包副本，
项目选中的 skills 来自 checkout 里的 `.opencode/skills/`。skills 用自己的名字，不带 `dotbrain:` 前缀。只能手动调用的 skills
在 OpenCode 里不受限制：它们照样出现在列表里，模型也可以调用。详见[OpenCode](getting-started.md#opencode)。

Pi 的 skills 来自 `dotbrain bootstrap --runtime pi` 放进 Pi Agent 目录的扩展，项目选中的 skills 来自
受信任 checkout 里的 `.pi/skills/`。只能手动调用的 skills 对模型隐藏，用 `/skill:<name>` 调用。详见
[Pi](getting-started.md#pi)。

Cursor 的打包 skills 来自你的 dotbrain Claude Code plugin；这个 plugin 缺失、被禁用或过时时，来自 dotbrain 保存的副本。
Cursor 也会读取 `.claude/skills`、`.codex/skills` 和 `.agents/skills`，所以 dotbrain 只把 Cursor 找不到的 skills 链接到
`.cursor/skills/`。只能手动调用的 skills 只能用 `/<name>` 运行。详见 [Cursor](getting-started.md#cursor)。

内置 skills 直接在 [`plugin/skills/`](https://github.com/arminzou/dotbrain/tree/main/plugin/skills) 里编辑。

## 复盘 {#retrospectives}

`run-retro`：让 Agent 不再重复犯同样的错误，同时让你能看到反馈循环是否跑偏并及时纠正。它有两种模式。

### Curate：整理经验

**Curate**（手动调用，或由你在 Agent 宿主上设置的定时任务调用）读取自上次整理时记录的时间点以来有变化的工作和审阅记录
（被拒绝的候选、`CHANGES` 结论、失败的检查、你的纠正、值得保留的成功做法），而不是逐个看 commit。
它在私有 `RETRO.md` 中合并、淘汰发现，与 `RULES.md`、测试、skill 文本和结构性修复去重，把 lead 在任务完成时记录在工作记录上的复盘候选整理成发现，并补回漏记的发现。它是笔记唯一的写入者，因此在不同设计或不同机器上工作的 lead 不会争抢同一份笔记。
对还没有任何保护的发现，它会建议最合适的强约束（结构、类型、检查或 hook、测试，最后才是规则文本）；
它只提出建议，不会自己实现，实现与否由你另行批准。
### Audit：检查效果

**Audit** 只在你要求时运行，范围由你选定，且只读：它根据后续的任务分派和审阅结论，判断提供给 Agent 的发现是否改变了行为，并建议保留、调整或停止。

### 报告与保存

没有值得你关注的内容时，运行不产生任何报告；否则报告简短、决策优先，每项决策都附推荐选项。未答复的决策保持待定，不构成任何授权。
手动运行时，如果 runtime 提供提问对话框，会先通过对话框请你处理待定决策。写入笔记时使用 compare-and-swap 保存，
运行失败或互相重叠都不会丢失内容，下次运行会重新处理。
### 公开提案与授权

默认关闭公开自动交付：建议只保存在私有笔记中，由你决定。只有获得单次提案授权，或在私有项目配置中将
`retro.promotion.auto-deliver` 设为 `true` 并通过 `destinations` 数组列出允许修改的已有公开文件，它才会自动准备和交付改动。
它以只读方式检查 PR 和合并状态；只有确认改动已合入目标分支，才会记录规则已被接受。PR 批准、合并和发布仍由你决定。
已采用的 `RULES.md` 按主题使用 `Rule` / `What to check` 表格，其他指南保留原有格式。规则提案使用 `run-retro` 自己的 PR 流程和格式，
不调用负责普通改动交付的 `pr` skill。
### 首次运行与整理范围

首次运行先读取根目录说明及其引用的标准，记录本次整理的时间点，不回溯历史。
若为仓库范围且没有规则或标准文件，会在首次运行（或之后尚未得到答复的运行）中询问一次是否创建 `RULES.md`，只收录已有说明中写明的要求，并以 PR 交付；
贡献者范围从不在仓库中创建文件。整理范围限于明确选定的贡献分支或 PR，或维护者选定的集成分支；未选定范围时会报告缺口，不会默认审阅整个仓库。
