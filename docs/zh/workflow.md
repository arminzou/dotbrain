# 选择工程工作流

Dotbrain 保存项目理解和可恢复的工作状态。五个核心 skills 提供连接、上下文维护、仓库要求和原生
Beads 操作；调查、规划、分派、验证、恢复与交付由你选择的工程工作流负责，并遵守用户和仓库的授权。
只使用核心能力的项目不需要 pstack。

```mermaid
flowchart TB
  accTitle: A selected workflow uses independent Dotbrain capabilities
  workflow["`**Selected workflow**
  planning and delivery`"]
  brain["`**Brain**
  context and evidence`"]
  graph["`**Beads**
  tasks and ownership`"]
  rules["`***RULES.md***
  adopted requirements`"]
  workflow -- reads and maintains --> brain
  workflow -- records work in --> graph
  workflow -- follows --> rules
```

`maintain-brain` 用来记录术语、已采纳的决策、设计、已验证的发现，以及仍未解决的假设和证据。
`work-graph` 维护任务、依赖、认领和执行证据。初始化仓库要求需要明确请求 `repo-rules`；单纯评估不会采纳新规则。
规则的代码、测试或 CI 执行机制由工程工作流实现。

## 可选的 pstack 集成 {#pstack}

Dotbrain 提供项目级的 `dotbrain-pstack` mode，将外部
[pstack](https://github.com/backnotprop/pstack) 能力接入 Brain 和 Beads。
它由 CLI 单独交付，不在 marketplace 的五个核心 skills 中。连接项目不会自动启用或安装 pstack，
也不会为只使用核心能力的项目选择工程工作流。

### 准备依赖 {#dependency}

单独克隆并保留指定版本的干净 checkout：

```bash
git clone https://github.com/backnotprop/pstack.git ~/pstack
git -C ~/pstack checkout 9cd6939b766cb920f1c44970d7c7ee1ec28bd0d6
```

集成要求这个完整 revision，manifest 版本为 `0.15.36`。Dotbrain 检查来源根目录、revision、
干净的 Git 状态、manifest 和所有 tracked 资源文件。请保持 checkout 不变，也不要添加 untracked 文件。
`wire`、`refresh` 和 `doctor` 不会 fetch、安装或更新依赖。其他版本或安装形式需要单独验证。

### 为项目启用 {#opt-in}

编辑现有的项目声明，保留无关设置：

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
pstack:
  enabled: true
  source: ~/pstack
```

`enabled` 必须是 YAML boolean，默认为 `false`。`source` 必须是绝对路径或以 `~/` 开头，
不能使用相对路径。启用时需要已初始化、可连接的 Beads 后端，`beads.mode` 为 `embedded` 或 `server`。
详见[配置](configuration.md#pstack)和 [Beads 设置](beads-backend.md)。

在每个已连接的 checkout 中同步并检查：

```bash
dotbrain refresh
dotbrain doctor
```

`dotbrain refresh --all` 处理已注册的项目。选中的 Claude Code 和 Codex 工作区分别收到
`.claude/skills/dotbrain-pstack/` 和 `.agents/skills/dotbrain-pstack/`，链接到私有 home 中独立的自有集成缓存。
被 gitignore 的 `.dotbrain-pstack.json` 记录依赖选择和交付位置；应编辑项目声明，不要修改这个生成文件。
启动上下文只增加有大小限制的发现指针，不注入工作流正文。改变选择后重启会话，再使用 runtime 展示的
`dotbrain-pstack` skill 开展工程工作。

mode 负责选择任务、由 coordinator 持有认领、本地 worktree 分派、独立验证、上下文记录与恢复。
它使用经过适配的外部能力，不同时运行 pstack 顶层的 `poteto-mode`。
范围、验收标准、权限与交付授权仍由用户和仓库决定；启用 mode 不授予发布、发消息、合并、部署或 release 权限。

### 验证范围 {#qualification}

首批 native 验证目标是 Windows 本地的 Claude Code `2.1.325`、Codex `0.169.0`、Beads `1.3.1`，
以及上述固定的 pstack 来源。验证必须记录集成后的 Dotbrain 精确 revision、runtime 与依赖版本、设置及可独立检查的 traces。
某个 revision 的实际结果以对应 release 或 PR 的验证证据为准。

来源检查和交付文件只能证明身份与文件系统状态。发现和调用、Beads 归属与关闭、跨会话读取，以及中断恢复
都需要 native runs 证明；doctor 健康不代表这些 Agent 行为已通过。其他操作系统、runtime、依赖版本与 cloud workers
不在首批 mode 验证范围内。六种核心 runtime 集成仍有各自的[安装方式与限制](getting-started.md)。

### 退出或升级 {#opt-out}

将 `pstack.enabled` 设为 `false`，在各 checkout 运行 refresh。Dotbrain 只删除能确认归属且完整的 mode 链接
和发现记录；修改过或属于其他工具的资源会保留并报告。开始新会话前，先明确检查这些资源。
外部 pstack 来源与其他安装仍由其原有工具管理；退出后请重启会话。

日常更新请保持依赖固定。升级 pstack 需要检查引用能力与适配契约，并重新执行受影响的验证，不能只改版本号。
核心的 breaking transition、正在进行的工作、备份与回滚见[升级说明](upgrading.md)。
