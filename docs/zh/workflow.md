# 选择工程工作流

Dotbrain 保存项目理解和可恢复的工作状态。五个核心 skills 提供连接、上下文维护、仓库要求和原生
Beads 操作；调查、规划、分派、验证、恢复与交付由你选择的工程工作流负责，并遵守用户和仓库的授权。
Dotbrain 不自带工作流，也不需要为你的工作流提供适配器。

`maintain-brain` 用来记录术语、已采纳的决策、设计、已验证的发现，以及仍未解决的假设和证据。
`work-graph` 维护任务、依赖、认领和执行证据。初始化仓库要求需要明确请求 `repo-rules`；单纯评估不会采纳新规则。
规则的代码、测试或 CI 执行机制由工程工作流实现。

## 工作流的记录放在哪里 {#records}

会话开始 hook 交付的约定决定任何工作流的记录放在哪里，即使工作流自己的说明指定了某个文件：

| 工作流输出 | 位置 |
| --- | --- |
| 计划、任务列表、进度和交接说明 | Beads issues |
| 设计推理、决策记录和调研 | 对应的 Brain 记录 |
| 代码和公开指南 | 代码仓库 |

之后的会话从 `bd ready` 和 Brain 继续，而不是从 transcript 或仓库里的文件继续。

## 使用基于 skills 的工作流 {#skill-workflow}

工作流的 skills 和其他 skills 一样选择。例如要使用 [pstack](https://github.com/backnotprop/pstack)，
把它加入你的 skill 库，再为当前 checkout 的项目选中它的 skill bundle：

```bash
dotbrain skills add https://github.com/backnotprop/pstack.git
dotbrain skills link pstack/skills
```

然后用工作流自己的入口调用它，例如 pstack 的 `poteto-mode`。Dotbrain 只通过 `dotbrain skills update` 改变工作流的版本。
范围、验收标准、权限和交付授权仍来自用户和仓库。更新和移除见 [skills](skills.md#external-repositories)，`skills:` 键见
[配置](configuration.md#project-yaml)。
