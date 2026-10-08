---
pageClass: prompt-examples
---

# 示例提示词

用 dotbrain，主要就是让你的 Coding Agent 去做事。本页收集了常见工作可以直接发送、或稍作修改的提示词。
每条都说明了什么时候用、会触发哪个技能，以及这一步在哪里有详细解释。

提示词保留英文，因为那就是你发给 Agent 的内容；换成中文说法，Agent 也一样能理解。

不一定要说出技能名：把要做的事描述清楚，Agent 通常就能选对技能。说出技能名则可以确保选中它。有两个技能，
`iterate-design` 和 `review-architecture`，从不会自动启动，需要显式调用，比如在 Claude Code 里用
`/dotbrain:iterate-design`。

## 配置 {#set-up}

### 连接仓库 {#wire-a-repo}

```text
Use wire-brain to wire this repo with Dotbrain.
```

**什么时候用：** 第一次在某个仓库或新的 worktree 里用 dotbrain。需要时会安装 CLI 和依赖。
**技能：** `wire-brain`。见[快速开始](getting-started.md)。

### 修复连接 {#repair-the-wiring}

```text
dotbrain doctor reports problems in this repo. Use wire-brain to find out why and repair the wiring.
```

**什么时候用：** `.brain` 或 `.beads` 缺失、链接失效，或者 Agent 不了解项目。插件或 CLI 更新后也可以用。
**技能：** `wire-brain`。见[项目连接](wiring.md)和[故障排查](troubleshooting.md)。

## 规划 {#plan}

### 摸清陌生代码 {#get-oriented-in-unfamiliar-code}

```text
Run find-unknowns on how GET /orders handles queries and responses before we add pagination.
```

**什么时候用：** 动不熟悉的代码之前，或者一项工作刚开始时。只读；它会报告那些会改变你做法的假设和约束。
**技能：** `find-unknowns`。见[工作流程](workflow.md#_1-orient)。

### 敲定决策 {#settle-decisions}

```text
Grill me on this plan: add pagination to GET /orders so clients can fetch orders in smaller batches.
Help me settle the pagination approach, default page size, and compatibility with existing clients.
Check it against our vocabulary and existing ADRs, and record what we settle.
```

**什么时候用：** 你有一个计划，但还有没想清楚的问题或需要定义清楚的术语。定下来的术语写进 `CONTEXT.md`，
难以撤回的选择写进 `adr/`。**技能：** `grill-decisions`。见[工作流程](workflow.md#_2-settle-decisions)。

### 写设计 {#write-a-design}

```text
Write a design for orders API pagination, with success criteria and known unknowns.
```

**什么时候用：** 工作跨多个会话、涉及多个模块，或者有真正的未知项。会在 `.brain/designs/` 里创建设计文档，
并开一个跟踪用的 epic。**技能：** `to-design`。见[工作流程](workflow.md#_3-write-the-design)。

### 把设计拆成任务 {#split-a-design-into-issues}

```text
Split the orders-pagination design into issues with acceptance criteria and dependencies.
```

**什么时候用：** 设计已经敲定并获批。每份设计只运行一次。**技能：** `to-issues`。
见[工作流程](workflow.md#_4-split-into-issues)。

## 执行 {#work}

工作流选择、任务归属和协作方式，见[和 Agent 团队一起工作](agent-team.md)。

**工作流**和**执行模式**是两个独立的选择。**HITL**（Human-in-the-Loop）每完成一次有明确范围的执行，就回到你这里；
**handoff** 则在你批准的约定内持续推进。**顺序执行**同一时间只有一个 Agent 写代码；**并行执行**则有多个写代码的
worker 同时工作。只读的研究、审阅或验证不算并行执行。见[工作流程](workflow.md#_5-work-the-issues)。

### 跟踪任务 {#track-work}

```text
What's ready to work on?
```

```text
File an issue: GET /orders returns duplicate orders on the next page. Link it to the orders-pagination epic.
```

**什么时候用：** 想看看哪些任务可以开始，或者创建、认领、更新、关闭任务。**技能：** `manage-work-graph`。
见[工作流程](workflow.md#_5-work-the-issues)。

### HITL：顺序执行 {#hitl-sequential-execution}

::: info 默认工作流和执行模式
默认使用 HITL 工作流和顺序执行。直接让 Agent 处理下一个任务即可，不用指定这两个选项；
完成这次范围明确的执行后，Agent 会回到你这里。
:::

```text
Work the next ready issue under the orders-pagination epic.
```

**什么时候用：** 你想一次指挥一段范围明确的工作。主 Agent 可以自己写，也可以交给一个 `worker`，两种都算顺序执行。
行为改动需要独立审阅。**技能：** `run-execution`。见[工作流程](workflow.md#_5-work-the-issues)。

### HITL：并行执行 {#hitl-parallel-execution}

::: info 默认 worker 数量上限
两种工作流的并行执行，默认最多同时运行两个 worker。
只有想调整这个上限时，才需要在提示词里指定数量。
:::

```text
Work the ready issues under the orders-pagination epic in parallel where they are independent. Show me the branch and how you'll split the work before starting.
```

**什么时候用：** 多个独立任务都已就绪，你想指挥这一批工作。如果无法安全并行，Agent 会说明原因，改为顺序执行。
**技能：** `run-execution`。见[工作流程](workflow.md#_5-work-the-issues)。

### Handoff：顺序执行 {#handoff-sequential-execution}

```text
/dotbrain:iterate-design Work the orders-pagination design, one issue at a time. Propose the handoff contract and wait for my GO.
```

**什么时候用：** 设计处于 active 状态，工作有机械化的检查，你希望 Agent 不用你盯着也能继续。它会先提出一份约定
（范围、分支、检查项、worker 数量、PR 交付方式），等你回复 `GO` 才开始。合并始终由你来做。**技能：**
`iterate-design`，只能显式调用。见[工作流程](workflow.md#_5-work-the-issues)。

### Handoff：并行执行 {#handoff-parallel-execution}

```text
/dotbrain:iterate-design Work the orders-pagination design, taking independent issues in parallel. Propose the handoff contract and wait for my GO.
```

**什么时候用：** 希望 Agent 按 active 设计持续推进，并把独立任务并行处理。某个任务耗尽重试次数或需要你决定时，
它和依赖它的任务会等待，其他独立任务继续。范围内只要还有任务被阻塞，handoff 就不能成功结束，也不能把 PR 标为 ready。
**技能：** `iterate-design`，只能显式调用。见[工作流程](workflow.md#_5-work-the-issues)。

两种 handoff 模式下，批准约定并回复 `GO` 后，Agent 可以推送专用分支、在首次推送时创建 draft PR，
并在验证和审阅通过后把 PR 标为 ready、请求你审阅。合并、部署、发布、依赖变更，以及范围或成功标准的调整，仍需你决定。

## 内置 Subagent {#packaged-subagents}

各角色的职责和运行时行为，见[内置 Subagent](agent-team.md#the-packaged-subagents)。

技能规定工作流程，subagent 则接收主 Agent 分配的具体任务。可以让主 Agent 用下面的名字调用它们：

| 职责 | Claude Code | Codex |
|---|---|---|
| 写代码 | `dotbrain:worker` | `dotbrain-worker` |
| 研究 | `dotbrain:researcher` | `dotbrain-researcher` |
| 审阅 | `dotbrain:reviewer` | `dotbrain-reviewer` |
| 验证 | `dotbrain:verifier` | `dotbrain-verifier` |

下面的提示词按角色描述任务；需要明确名称时，使用上表对应的名字。这些是交给 subagent 的任务，不是 slash command。
见[会话上下文](session-context.md#subagents)。

### 把一个改动交给 worker {#delegate-one-change-to-a-worker}

```text
Have the packaged worker fix duplicate orders across pages in GET /orders on our current branch. Give it the issue, its own Beads actor, and the agreed checks. Have it commit the fix and report back.
```

**什么时候用：** 有一个具体改动想交给 subagent。`worker` 会修改并提交候选结果，不会推送、合并或关闭任务。
如果要执行一批已跟踪的任务，优先用 `run-execution`，由它准备任务分配、协调审阅和集成。

### 研究 API 决策 {#research-an-api-decision}

```text
Ask the packaged researcher whether cursor or offset pagination fits GET /orders better. Check our Brain, the code, and official docs, and explain the trade-offs with sources.
```

**什么时候用：** 需要结合项目上下文、代码和外部资料，得到有来源依据的答案。`researcher` 报告发现并提出更新建议，
不会直接实施。

### 获取独立审阅 {#get-an-independent-review}

```text
Have the packaged reviewer check this orders-pagination branch against main and our acceptance criteria. Look for pagination bugs, authorization gaps, compatibility problems, and missing tests.
```

**什么时候用：** 希望由没有参与写这次改动的 Agent 做一次针对性的审阅。`reviewer` 检查 diff 及相关代码。
工作流中的单任务审阅还需要任务 ID、reviewer actor、审阅轮次、候选版本和 diff 基线；`run-execution` 会准备这些信息。

### 运行机械化验证 {#run-a-mechanical-verification-gate}

```text
Have the packaged verifier run the agreed checks for orders pagination on this branch and give me the results and a Verification block for the PR.
```

**什么时候用：** 需要证据证明约定的检查通过。`verifier` 运行检查、报告实际观察到的结果，不修复失败，也不给代码审阅结论。

## 审阅与结束 {#review-and-close}

### 审阅改动 {#review-a-change}

```text
Run a code review gate on this branch against main.
```

```text
Run a simplify review on this branch: what can we delete or replace?
```

**什么时候用：** 分支提交合并之前，或者任何时候想要一次独立审阅。模式有 `code`（正确性）、`simplify`（简化）
和 `readiness`（某个子系统是否足够可靠，能在上面继续构建）。**技能：** `review-gate`。
见[工作流程](workflow.md#_6-review)。

### 结束设计 {#close-a-design}

```text
The orders-pagination work is merged. Close the design: record the evidence and promote what should
outlive it to ADRs and CONTEXT.md.
```

**什么时候用：** 一项工作已经上线、被放弃或被取代。也可以用来清理那些一直没结束的设计。**技能：**
`close-design`。见[工作流程](workflow.md#_7-close-the-design)。

## 学习 {#learn}

### 开始学一个主题 {#start-learning-a-topic}

```text
Teach me how this project handles failed deliveries. I want to be able to diagnose one myself.
```

**什么时候用：** 你想真正理解项目的某一部分，而不只是要一个答案。**技能：** `teach-me`。
见[学习你的项目](learning.md)。

### 继续学习路径 {#continue-a-learning-path}

```text
Continue my learning path on retries. Read my progress and learning records, then resume the next step.
```

**什么时候用：** 在新会话里接着学。**技能：** `teach-me`。见[学习你的项目](learning.md#walk-a-learning-path)。

### 先把问题存起来 {#park-a-question-for-later}

```text
Park this for learning: why does retrying this operation require an idempotency key?
```

**什么时候用：** 做事途中冒出一个问题，但现在不想切换到学习。**技能：** `teach-me`。
见[学习你的项目](learning.md#park-a-question-while-working)。

## 维护 Brain {#maintain-the-brain}

### 创建或修复 Brain 站点 {#set-up-or-fix-the-brain-site}

```text
Set up a Brain site for this project and put the runbooks in the sidebar.
```

```text
dotbrain site build fails. Find the cause and fix it.
```

**什么时候用：** 想在浏览器里读 Brain、调整侧边栏，或修复构建失败。**技能：** `brain-site`。
见 [Brain 站点配置](brain-site-configuration.md)。

### 检查上下文健康 {#check-context-health}

```text
Check this project's context health: find stale, duplicated, or misplaced guidance across
AGENTS.md and the Brain, and anything private leaking into the public repo.
```

**什么时候用：** 指引越积越多，`AGENTS.md` 和 `CLAUDE.md` 不一致了，或者想检查公开/私有的边界。默认只报告，
只有你要求时才修复。**技能：** `curate-project-context`。

### 编写或修改给 Agent 看的文档 {#write-or-edit-agent-facing-docs}

```text
Use write-agent-docs to tighten this project's AGENTS.md.
```

**什么时候用：** 创建或修改 `AGENTS.md`、Brain 上下文、设计文档、技能，或 Agent 会依赖的公开文档。
**技能：** `write-agent-docs`。

### 分诊公开任务 {#triage-public-issues}

```text
Triage the open GitHub issues and promote the accepted ones into our work graph.
```

**什么时候用：** 项目接收公开任务，你想让它们被分类、复现，并纳入私有执行。需要在
[`project.yaml`](configuration.md#project-yaml) 里配置 `public-tracker`。**技能：** `triage-public`。

### 寻找架构改进点 {#look-for-architecture-improvements}

```text
/dotbrain:review-architecture
```

**什么时候用：** 想结合 Brain 的术语和 ADR，审查代码库里可以加深架构的地方。**技能：** `review-architecture`，
只能显式调用。

## 相关内容 {#related}

- [技能](skills.md)列出了所有技能及一句话说明。
- [工作流程](workflow.md)展示了这些技能如何配合。
