# 术语表

| 术语 | 含义 |
| --- | --- |
| Dotbrain home | 私有数据根目录，通常是 `~/dotbrain`，保存配置、自选资源来源、Brainspaces 和独立 Git 历史。 |
| Brainspace | 项目的私有工作区，包含 `.brain/` 知识和可选的 `.beads/` 后端状态。 |
| Brain | `.brain/` 中的术语、决策、设计、发现与参考资料。 |
| Brain-only project | 不连接 checkout 的 Brainspace；核心仍可通过 `beads.mode: none` 关闭 tracker。 |
| ADR | 已采纳的重要决策及其理由、证据和适用范围；提案不等于已采纳决策。 |
| Design | initiative 的意图、约束、未知问题与验证结果；任务状态留在 Beads。 |
| Work graph | 原生 Beads 任务、依赖、认领、验收标准和执行证据；readiness 表示依赖资格。 |
| Home sync | 私有 home 文件的 Git 版本管理与交换，独立于 Beads 后端持久化和备份。 |
| Core skill | `wire-brain`、`brain-convention`、`maintain-brain`、`work-graph`、`repo-rules` 之一，不依赖 pstack。 |
| Engineering workflow | 所选的规划、分派、验证、恢复和交付程序，受用户和仓库授权约束。 |
| Pstack mode | Dotbrain 提供的可选 `dotbrain-pstack` 集成，需要固定的外部 pstack 来源和项目明确启用。 |
| Runtime | Claude Code、Codex、Hermes、OpenCode、Pi 或 Cursor，各有集成方式和限制。 |
| Custom subagent | 用户选择的 Claude Code 或 Codex 定义；核心不提供工作流 agents。 |
| Worktree | 独立 Git checkout，可共用已有 Brainspace，同时单独接收 runtime 资源。 |
| Adopted requirement | 已采纳的公开仓库要求，通常放在 `RULES.md`，与改进提案分开维护。 |
| Agent routing | `AGENTS.md` 中指向仓库要求和相关指南的简洁指针。 |
| Derive | 基于已采纳的理解重新撰写公开说明，不暴露私有来源、路径或标识。 |
| Structural verification | 检查来源身份、打包文件、交付与配置，不证明 Agent 原生使用。 |
| Native qualification | 在精确 revision、版本和设置下观测 runtime 行为，并保留可检查的证据。 |

各项约定详见[架构](architecture.md)、[配置](configuration.md)和[工作流选择](workflow.md)。
