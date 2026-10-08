# 术语表

术语名保留英文，因为命令、文件和技能里用的都是这些名字。

## 核心术语 {#core-terms}

### Dotbrain

工具本身。dotbrain 把一个私有的 Brainspace 以及技能和运行时配置连接到代码仓库，而不会把这些私有状态搬进仓库。

### Dotbrain home

私有的数据目录，按约定是 `~/dotbrain`。它在 `brainspaces/` 下存放所有项目的 Brainspace，在 `skills/` 下存放
用户自己管理的技能，在 `agents/` 下存放子 Agent 的源文件，还有全局的 `config.yaml`。它是一个独立于代码
checkout 的 Git 仓库。设置 `DOTBRAIN_HOME` 或传 `--home <path>` 可以换一个位置。

### Brainspace

每个项目私有的目录，位于 `~/dotbrain/brainspaces/<name>/`。Brainspace 包含项目的 Brain（`.brain/`），
启用时还包含执行存储（`.beads/`）。Agent 工作区（`.claude/` 和 `.codex/`）是代码 checkout 里的真实目录。

### Brainspace links

放在仓库里、指回私有 Brainspace 的那些被 gitignore 的链接。通常是 `.brain` 和 `.beads`；`.claude` 和 `.codex`
是项目自己的目录，里面放着逐个被忽略的 dotbrain 资源。

### Brain

项目的长期知识层。Brain 存放项目上下文、决策和面向 Agent 的约定。在 dotbrain 的术语里，Brain 的范围比整个
Brainspace 小。

### Brain-only project

没有代码 checkout 的项目，用 `dotbrain wire --no-repo --project <name>` 创建。它仍然可以有执行存储。加上
`--skip-beads` 可以创建一个没有任务跟踪的项目；没有任务跟踪的项目也可以连接 checkout。

### ADR

架构决策记录（Architecture Decision Record），放在 Brain 的 `adr/` 里。每个决策一个文件，记录那些难以撤回、
没有上下文会让人意外、并且经过真实取舍的决策。

### Design doc

一项工作的设计，放在 Brain 的 `designs/` 里。它的 `lifecycle` 是 `draft`、`active`、`shipped`、`abandoned`
或 `superseded` 之一。active 的设计是持续更新的规格；进入终态的设计是一份记录。见[工作流程](workflow.md)。

### Bead

Beads 执行存储里的一个任务。epic 把 bead 归组，`blocks` 依赖决定哪些已经可以开始。

### Brain site

`dotbrain site` 根据 Brain 渲染出来的私有本地文档站点。见 [Brain 站点](brain-site.md)。

### `config.yaml`

dotbrain 的全局配置文件，通常在 `~/dotbrain/config.yaml`。它存放整台机器的默认配置，比如共享的 beads 服务器设置。

### `project.yaml`

每个项目的配置文件，位于 `~/dotbrain/brainspaces/<name>/.brain/project.yaml`。它声明项目级的设置，比如执行引擎、
公开任务跟踪、初始化哪些 Agent 工作区、与默认值不同的 beads 配置，以及额外的技能。

### Execution engine

存放项目私有工作图的后端。目前是 beads，但这个术语描述的是角色，而不是某个具体实现。

### Execution store

由执行引擎管理的实时状态。实际上，就是未完成的工作、依赖、就绪状态和关闭状态存放的地方。

### Work graph

执行存储里的工作项，以及它们之间的依赖关系：有哪些工作、各自在等什么。ready frontier 是所有没有未关闭
阻塞项的未完成工作项。

### Execution graph

一个 Agent 团队如何完成一组固定的工作项：分派、合并、检查，以及各个工作项按什么顺序关闭并解除对后续项的阻塞。
它存在于 lead 的会话里，而不是任务跟踪里。

### Execution record

执行中的工作项上可以恢复的信息：它原生的状态和负责人、几个记录阶段、尝试次数和产物的 `dotbrain_` 元数据键，
以及带标题的证据评论，包括它的 item review。

### Human-in-the-loop (HITL) workflow

由你一步步指挥 Agent、并随时看到改动的工作流程。每完成一次 bounded execution，Agent 都会回到你这里；
它的工作仍然通过你审阅的 PR 进入 `main`。见[工作流程](workflow.md#_5-work-the-issues)。

### Handoff workflow

Agent 在你用明确的 `GO` 批准的约定范围内继续工作，直到完成、遇到需要人来把关的关卡，或者触发硬性停止条件。
`iterate-design` 负责运行它，并通过一个转为 ready、等你审阅的 PR 交付工作。

### Execution mode

一次 bounded execution 中同时有几个 Agent 在写：顺序执行，同一时间只有一个写入者；或者并行执行，两个或更多
负责写的 worker 各自在自己的 worktree 里。两种工作流程都可以用任意一种模式。

### Bounded execution

`run-execution` 对一组固定工作项的一次运行。当每个工作项都已关闭，或者仍未关闭但记录了阻塞原因、人工关卡或取消时，
它就结束了。

### Item review

在工作项关闭前，由一个没参与编写的 reviewer Agent，对这个工作项在代码、测试、构建或 CI 配置、Agent 指令上的
改动做的独立代码审阅。审阅者把结论 `APPROVE` 或 `CHANGES` 记录在工作项上。

### Lead, assignee, worker, agent team

agent team 是一次 bounded execution 中的 lead 和它分派的 worker。lead 负责选择、合并、检查和关闭工作项，并且在
委派的 worker 运行期间，只有它能修改工作图。worker 完成分配给它的操作并汇报结果。assignee 是持有工作项认领的
执行者；worker 会一直持有认领，直到工作项关闭，而合并和关闭由 lead 来做。

### Agent runtime

dotbrain 连接的 Coding Agent 环境，比如 Claude Code 或 Codex。

### Agent workspace

仓库里特定运行时的工作区目录，比如 `.claude/` 或 `.codex/`。dotbrain 只在里面链接选定的资源。

### Public tracker

面向外部的任务系统，用于接收公开的问题和与贡献者协作，比如 GitHub Issues。已有的公开任务可以带着来源链接被
提升到私有工作图里。私有的设计、epic 和工作项从不作为公开的跟踪任务暴露出去；即使没有公开任务，PR 也可以
提供公开的审阅入口。

### Worktree

共享同一个仓库历史、但有自己工作目录的 git worktree。在 dotbrain 里，`dotbrain wire` 通过 Git 元数据把它直接
连到主 checkout 已有的 Brainspace。

### Bootstrap

由 `dotbrain bootstrap` 运行的本机配置步骤。它初始化全局配置并链接全局技能。

### Skill

一种可复用的 Agent 能力，有自己的指令，有时还带参考资料。

### Brain-coupled skill

直接操作项目 Brain 或执行状态的技能。dotbrain 把这类技能中必需的那一组作为其运作模型的一部分一起发布。

### Adopter repo

被 dotbrain 连接到私有 Brainspace 的普通代码仓库。adopter repo 专注于代码；Brain 和执行状态放在它之外。

### Derive

根据私有的源材料，写出一份面向公开读者的说明或产物，而不直接暴露私有原文。dotbrain 用这条边界让 Brain 保持私有，
同时仍然可以公开发布文档或工具。

## 不收录的术语 {#excluded-terms}

本术语表有意不收录较底层的实现术语和私有的内部说法。它的目的是解释公开的概念模型，而不是每一条 CLI 修改路径
或历史用语。
