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

已经停用的项目类型，没有代码 checkout。`dotbrain wire --no-repo` 已经移除：每个项目都以一个仓库作为工作目录。
这个仓库可以是私有的，只放文档。要迁移 Brain-only 的 Brainspace，在新仓库里运行
`dotbrain wire --project <name>`；或者把 Brainspace 移出 `brainspaces/` 归档。加上 `--skip-beads` 可以创建一个
没有任务跟踪的项目。

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

执行中的工作项上可以恢复的信息：它原生的状态和负责人、几个记录阶段、尝试次数、产物和待处理复盘候选的 `dotbrain_` 元数据键，
以及带标题的证据评论，包括它的 item review。

### Human-in-the-Loop (HITL) workflow

由你一步步指挥 Agent、并随时看到改动的工作流程。每完成一次 bounded execution，Agent 都会回到你这里；
它的工作仍然通过你审阅的 PR 进入 `main`。见[工作流程](workflow.md#_5-work-the-issues)。

### Handoff workflow

Agent 在你批准的约定范围内继续工作（通过明确的 `GO`，或复用已批准的约定），直到完成、遇到需要人来把关的关卡，或者触发硬性停止条件。
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

## 交付与验证 {#delivery-and-verification}

### Home sync

通过 `dotbrain sync`，让 dotbrain home 与它自己的私有 remote 交换 Git 历史。
交换前会先提交 home 中尚未提交的改动。任务跟踪的同步（`dotbrain beads sync`）是另一项操作，只拉取，不推送。

### Plugin and packaged subagent

Plugin 是运行时原生支持的包，用来交付 dotbrain 的共享技能、约定和运行时集成。
packaged subagent 是 dotbrain 随包提供的 Agent 定义：负责写入的 `worker`，以及只读的
`researcher`、`reviewer` 和 `verifier`。packaged worker 完成分配的工作并提交候选改动，由 lead 负责交付。
运行时如何发现和加载这些定义，见[会话上下文](session-context.md#subagents)。

### Review bead

记录设计级审阅或独立审阅的工作项，包含范围、评判标准、发现、证据、适用时的结论，以及每条发现的处理结果。
item review 和 integration review 直接记在各自涉及的工作项上，不另建 review bead。

### Integration review

针对一组暂时合在一起的工作项，在同一个确切版本上做的独立代码审阅。
在这些工作项关闭或解除对后续工作的阻塞之前，审阅必须覆盖每项的验收条件、受影响的使用方，以及改动之间的相互影响。

### Integration candidate

从已验收版本出发、存放待验收改动的独立分支。lead 把它提升到 delivery branch 前，
审阅和检查必须覆盖它确切的 head。补丁或集成上下文变了，就需要重新审阅和检查。

### Accepted head

通过审阅和所需检查的那个 commit：可以是 review bead 所记录范围的末端，
也可以是已验证工作项所记录的集成版本。

### Delivery branch

存放已验收结果的专用分支。提升候选改动时，只能将它 fast-forward 到已验收的确切 head；
失败或尚未被审阅和检查覆盖的候选分支继续单独保留。

### Checkpoint

一次执行中有明确边界的实现步骤，以及针对它的小范围检查。每个命名的 checkpoint（比如测试或 item review）
分别记录重试历史。checkpoint 本身不是工作项，也不是 commit；检查由做出改动的 Agent 来跑。

### Verifier gate and verification evidence

verifier gate 是约定好的、能机械判定通过或失败的检查，比如测试、构建或指标。
verification evidence 记录实际跑了什么、输出和缺口，以及证据对应的版本和环境。
verifier 角色负责跑检查并返回证据，审阅负责补充判断。各层检查由谁来跑，见[工作流程](workflow.md)。

### Acceptance and UAT

Acceptance 表示约定的条件和证据已满足，可以把工作项或集成候选结果验收到 delivery branch。
UAT（用户验收测试）在明确的运行时、版本和操作系统环境中验证约定的用户流程。
Agent 可以执行并记录这些检查；PR 的批准和合并仍由人决定。

### Review surface

展示改动、供人审阅的地方：通常是 PR；项目没有 PR 托管时，就是分支 diff。
完整测试套件的结果和适合公开读者的验证证据放在这里。

### Oracle

审阅所依据的书面标准，包括适用的决策、设计目标、验收条件和规则。
审阅开始前就固定下来，让审阅结果回答最初的问题。

### Canon and durable residue

Canon 是项目中具有权威性的词汇、决策和规则，与根据它们写出的说明文档有别。
durable residue 是设计结束后仍有用的知识，要整理到相应的词汇、决策或规则文档中。
设计收尾的流程见[工作流程](workflow.md)。

## 不收录的术语 {#excluded-terms}

本术语表有意不收录较底层的实现术语和私有的内部说法。它的目的是解释公开的概念模型，而不是每一条 CLI 修改路径
或历史用语。
