# 技能

dotbrain 插件会分发它那些与 Brain 配合的技能，相当于已连接项目的操作手册。它们涵盖连接、规划、执行、分诊和
Brain 维护。其中有几个借鉴并改编自 [mattpocock/skills](https://github.com/mattpocock/skills)。

[工作流程](workflow.md)展示了它们如何配合。

技能的链接由你自己管理：

- 全局技能在 `~/dotbrain/skills/skills.yaml` 里选择
- 项目技能在 `brainspaces/<name>/.brain/project.yaml` 里选择

## 选择和同步技能 {#select-and-reconcile-skills}

两种范围都可以选单个技能，也可以选一个技能包目录：

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/skills/skills.yaml
global_extra:
  - another-collection
```

包含 `SKILL.md` 的目录只选中它自己，即使它下面还有子技能。否则，dotbrain 会递归查找所有包含 `SKILL.md` 的
子目录，`node_modules` 除外。重复选中同一来源会去重。不同来源映射到同一个目标名（包括在不区分大小写的文件系统
上只有大小写不同）时，会在改动目标之前失败。路径不存在、不是目录或技能包为空时，也会失败并给出可操作的提示。

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

在选中的技能包里增删技能，下次同步时就会生效，声明本身不变。被移除的、dotbrain 自己的链接会被清理，
其他来源的条目会保留。`projects show`、技能目录和 doctor 都使用同样的展开结果。

## 配置 {#setup}

- **`wire-brain`**：创建或修复仓库与其私有 Brain 之间的 Brainspace 连接，包括恢复链接出来的 worktree 的
  `.brain` 和 `.beads`。第一次使用时，如果缺少 `dotbrain` CLI 会自动安装。
- **`dotbrain`**：操作约定本身。会话启动 hook 会自动注入它；在不运行 hook 的运行时里，可以直接调用它。

## 规划 {#planning}

- **`to-design`**：把一项多步骤的工作写成一份持续更新的 active 设计文档，存进 Brain，并创建一个 epic bead。
  适合在拆分之前需要明确设计、或需要一个地方跟踪未知项的工作。
- **`to-issues`**：把设计文档拆成可以独立处理的 bead 任务，带验收标准和依赖，并用
  `--spec-id design:<slug>` 把每个 bead 关联回设计。
- **`grill-decisions`**：对照项目的术语和决策对计划做压力测试，再把长期有效的结论写进 `CONTEXT.md` 和 `adr/`。
- **`find-unknowns`**：在确定设计之前，找出陌生领域里的盲点和隐含假设。
- **`close-design`**：手动把设计文档推进到终态；认定已交付前核实 PR 合并证据，记录结果，
  把需要保留的内容提升到 `adr/` 和 `CONTEXT.md`，关闭 epic。

## 执行 {#execution}

- **`manage-work-graph`**：在私有工作图里创建、查看、认领、拆分、更新和关闭工作项
- **`run-execution`**：完成一个工作项或一批固定的工作项：分派 worker，让每个改动都经过独立审阅，合并，检查，
  在限度内修复，必要时上报或恢复
- **`iterate-design`**：用 Agent 原生的循环模式推进一份 active 设计文档：规划、实现、验证、反思，通过一个
  draft PR 交付，完成后转为 ready 等你审阅，在成功或阻塞时停下

## 分诊与审阅 {#triage-and-review}

- **`run-retro`**：检查新增或变化的证据，在私有 Brain 中记录 Agent 的发现、成功做法和已处理的范围。
  可手动调用，也可由外部定时任务调用。同一做法在三个不同证据日期得到支持后，默认只查找仓库已有的规则、标准或贡献指南，
  建议合适的文件和规则，由你决定是否创建 PR。它还会建议最有效的自动化约束（结构、类型、检查或 hook、测试），一旦违反规则就直接报错；
  它只提出建议，不会自己实现，实现与否由你另行批准。只有获得单次提案授权，或在私有项目配置中将
  `retro.promotion.auto-deliver` 设为 `true` 并通过 `destinations` 数组列出允许修改的已有公开文件，它才会自动准备和交付改动。
  它以只读方式检查 PR 和合并状态；只有确认改动已合入目标分支，才会记录规则已被接受。
  PR 批准、合并和发布仍由你决定，定时调度由 Agent 宿主负责。
  私有 `RETRO.md` 只用 Markdown 条目记录发现，文首简要记录审阅范围和未完成事项，不重复保存 YAML 台账。
  审阅按声明的范围进行，不保证发现所有历史记录的编辑。
  已采用的 `RULES.md` 按主题使用 `Rule` / `What to check` 表格，其他指南保留原有格式。规则提案使用 `run-retro` 自己的 PR 流程和格式，
  不调用负责普通改动交付的 `pr` skill。
  首次运行先读取根目录说明及其引用的标准，以当前 HEAD 为起点，不回溯历史。
  若为仓库范围且没有规则或标准文件，会在首次运行（或之后尚未得到答复的运行）中询问一次是否创建 `RULES.md`，只收录已有说明中写明的要求，并以 PR 交付；
  贡献者范围从不在仓库中创建文件。
  后续按明确选定的贡献分支或 PR，或维护者选定的集成分支向前审阅，复用共享进度并读取当前适用的规则。
  未选定范围时会报告缺口，不会默认审阅整个仓库
- **`review-gate`**：运行一次持久的审阅关卡（代码、简化或就绪性），并把结果记录在任务上；必要证据覆盖准确版本、
  各条发现处理完毕后，lead 可在 PR 合并前关闭已通过的审阅。PR 批准、合并和发布仍由你决定
- **`curate-project-context`**：在公开项目和私有 Brain 中找出并修复过时、重复、放错位置、无法访问或泄露的上下文
- **`triage-public`**：对公开任务跟踪里的条目分类，把准备好的工作提升到私有执行中
- **`review-architecture`**：审查代码库，寻找可以加深架构的机会

## 写作 {#authoring}

- **`write-agent-docs`**：为公开项目文档、私有 Brain 内容、用户自己的技能，以及 Agent 通过指针读到的指引
  提供写作规范

## Brain 站点 {#brain-site}

- **`brain-site`**：手动调用，用 `dotbrain site` 创建、维护、构建或预览 Brain 的私有站点，
  包括侧边栏、主题和页面渲染检查

## 学习 {#learning}

学习路径、暂存的概念和会话之间的延续，请看[学习你的项目](learning.md)。

- **`teach-me`**：跨多个会话，根据 Brain 教你了解自己的项目：在对话中讲解，按一条以 `learn:` bead 跟踪的
  学习路径推进，记录你展示出的理解，并把认可的课程保存到 `.brain/learning/`

## 子 Agent {#subagents}

除了技能，dotbrain 还自带能读 Brain 的子 Agent：`worker`、`reviewer`、`verifier` 和 `researcher`。见
[会话上下文](session-context.md#subagents)。

## 安装 {#installing-them}

技能随插件一起提供，每个 Agent 运行时装一次，而不是每个仓库装一次。安装命令见[快速开始](getting-started.md)。
插件装在用户级别，所以它的技能在每个会话里都可用，包括还没连接的仓库。

Hermes 的技能来自 `dotbrain bootstrap --runtime hermes` 放进 Hermes 主目录的插件副本，
项目选中的技能来自已信任 checkout 里的 `.hermes/skills/`。只能手动调用的技能会出现在 Hermes 的列表里，
但模型加载不了，要你自己调用。详见[Hermes](getting-started.md#hermes)。

OpenCode 的技能来自 `dotbrain bootstrap --runtime opencode` 放进 OpenCode 配置目录的打包副本，
项目选中的技能来自 checkout 里的 `.opencode/skills/`。技能用自己的名字，不带 `dotbrain:` 前缀。只能手动调用的技能
在 OpenCode 里不受限制：它们照样出现在列表里，模型也可以调用。详见[OpenCode](getting-started.md#opencode)。

Pi 的技能来自 `dotbrain bootstrap --runtime pi` 放进 Pi Agent 目录的扩展，项目选中的技能来自
受信任 checkout 里的 `.pi/skills/`。只能手动调用的技能对模型隐藏，用 `/skill:<name>` 调用。详见
[Pi](getting-started.md#pi)。

内置技能直接在 [`plugin/skills/`](https://github.com/arminzou/dotbrain/tree/main/plugin/skills) 里编辑。
