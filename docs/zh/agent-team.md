# 与 Agent 团队协作

分派由你选择的工程工作流和 Agent runtime 负责。Dotbrain 提供共享 Brain、原生 Beads 访问，
以及选定的自定义 agents 交付。五个核心 skills 不附带 worker、reviewer、verifier 或 researcher 定义。

## 共享上下文与工作状态 {#shared-context-and-work-state}

连接的 Git worktrees 共用项目 Brain 和 Beads store，各 checkout 单独接收 runtime 资源。
`maintain-brain` 提供记录操作，`work-graph` 提供原生工作图和归属操作。
依赖允许开工，不等于已获授权、有可用 writer，或结果已被验收。

工作流决定给 delegates 哪些上下文、谁写入各资源、用什么检查验收，以及如何恢复中断的工作。
交接应保留实际 candidate、认领、证据和剩余限制。并发修改共享记录时，保存前必须协调当前内容。

## 自定义 agents {#the-packaged-subagents}

通过全局 `config.yaml` 或项目 `project.yaml` 中的 `subagents:` 选择自己的 Claude Code 或 Codex 定义。
来源放在 `~/dotbrain/subagents/claude/` 和 `~/dotbrain/subagents/codex/`。
`dotbrain-` 前缀仍保留，用来保护需要检查的旧版资源。

```bash
dotbrain subagents list
dotbrain subagents link
dotbrain subagents link --scope global
```

Claude 定义使用链接；Codex 使用带 `# dotbrain-managed-agent: v1` 标记的生成 TOML 文件。
请修改来源，而不是生成资源。修改过、属于其他工具或发生名称冲突的资源需要明确检查；
详见[配置](configuration.md#global-subagents)和[会话上下文](session-context.md#subagents)。

文件交付不代表 runtime 已加载或成功启动 Agent。Hermes、OpenCode、Pi、Cursor 和 Antigravity 接收核心 skills 和会话集成。
Dotbrain 只向 Claude Code 和 Codex 交付原生自定义 subagents。
