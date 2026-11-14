# 示例提示词

按需要请求具体操作。五个核心 skills 维护工作区资源、项目理解、仓库要求和工作记录；工程实现交给所选工作流。
使用 runtime 展示的 skill 名称。Claude Code 插件使用 `/dotbrain:<name>`，Codex 可从 picker 选择。

## 连接或修复仓库 {#wire-or-repair-a-repository}

```text
Use wire-brain to wire this repository with Dotbrain and check its health.
```

`wire-brain` 通过 CLI 完成设置和修复。连接本身不启用 pstack；详见[快速开始](getting-started.md)。

## 记录项目理解 {#capture-project-understanding}

```text
Use maintain-brain to record the verified API constraint and its evidence.
Keep the retry explanation as an unresolved hypothesis.
```

同一能力还维护术语、已采纳的决策、设计、参考资料和生命周期记录。
记录发现不等于采纳新决策；终态声明需要相应证据和授权。

## 查看或维护工作记录 {#inspect-or-maintain-work-records}

```text
Use work-graph to inspect this initiative's dependencies and current ownership.
Report ready work without starting implementation or changing claims.
```

需要写入时，明确任务操作和适用 actor。原生 Beads readiness 表示依赖资格，工作流再应用范围、容量和验收要求。
详见 [Beads 后端](beads-backend.md)。

## 初始化仓库要求 {#initialize-repository-requirements}

```text
Use repo-rules to initialize RULES.md and its AGENTS.md routing.
Adapt the baseline to this repository, preserve existing requirements,
and report conflicts without adopting a resolution.
```

初始化需要明确请求。单独调用只评估，不采纳提案，也不创建规则文件。
公开 `AGENTS.md` 应指向要求，不重复规则正文。

## 评估执行机制 {#assess-enforcement}

```text
Use repo-rules to assess enforcement of the adopted dependency boundary.
Report the existing checks and smallest enforcement gap without editing files.
```

如请求实现 enforcement，会将已采纳的规则、授权、边界与已有检查、建议机制和验证需求交给工程工作流。
评估本身不修改代码、lint 或 CI。

## 使用所选工程工作流 {#use-a-selected-engineering-workflow}

[明确设置 pstack](workflow.md#opt-in) 后，开启新会话，选择 runtime 展示的 `dotbrain-pstack` skill：

```text
Use this project's dotbrain-pstack mode to implement the approved API change.
Preserve the existing acceptance criteria and record actual checks and pending work.
```

mode 负责执行与恢复程序。只用核心能力的项目也可选其他工作流，复用同样的上下文和工作图操作。
调用 skill 本身不授予发布、发消息、合并或 release 权限。
