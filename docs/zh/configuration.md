# 配置

大多数情况下都不需要改配置。真要改时，一共有四个文件，都在你私有的 dotbrain 主目录里：

```mermaid
treeView-beta
  accTitle: Where dotbrain's configuration files live
  ~/dotbrain/
    config.yaml ## machine: shared infrastructure
    skills/
      skills.yaml ## machine: global skills
    agents/
      agents.yaml ## machine: global subagents
    brainspaces/
      my-app/
        .brain/
          project.yaml ## one project
```

| 文件 | 范围 | 由谁初始化 |
| --- | --- | --- |
| `~/dotbrain/config.yaml` | 本机：共享的基础设施 | `dotbrain bootstrap` |
| `~/dotbrain/skills/skills.yaml` | 本机：全局技能 | `dotbrain bootstrap` |
| `~/dotbrain/agents/agents.yaml` | 本机：全局子 Agent | `dotbrain bootstrap` |
| `brainspaces/<name>/.brain/project.yaml` | 单个项目 | `dotbrain wire` |

修改项目声明后，运行 `dotbrain refresh`（或 `dotbrain refresh --all`）。全局资源的变化用
`dotbrain skills link --scope global` 或 `dotbrain agents link --scope global` 同步。

## 环境变量 {#environment}

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DOTBRAIN_HOME` | `~/dotbrain`（Windows 上是 `%USERPROFILE%\dotbrain`） | Brainspace 和配置存放的位置 |

## `config.yaml`

只有使用 [server 模式](beads-backend.md#server-mode)的 Beads 时才需要。初始化出来的文件里，这一段是注释掉的。

```yaml
# ~/dotbrain/config.yaml
version: 3

beads:
  server:
    host: db.example.internal
    port: "3307"
    user: beads
    ssh_host: bastion.example.internal   # optional SSH hop, used by beads drop-db
```

::: warning
不要把凭据写进 `config.yaml`，请放在你的密钥存储里。
:::

## `project.yaml`

项目的身份，以及与全局默认值不同的地方。一个使用 server 模式 Beads、额外加了一个技能的项目是这样的：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
execution-engine: beads

agents:            # which agent workspaces dotbrain wires
  - claude
  - codex

public-tracker: gh            # none | gh | linear
public-tracker-id: owner/repo

beads:                        # deviations from global defaults only
  mode: server                # embedded | server | none
  remote: https://doltremoteapi.dolthub.com/owner/repo
  database: project_beads

skills:                       # extra skills for this project's workspaces
  - some-collection/some-skill

# subagents:                  # project-only subagents; packaged subagents are always wired
#   - some-project-only-subagent
```

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `execution-engine` | `beads` | 私有的执行后端 |
| `agents` | `[claude, codex]` | 要连接到仓库的 Agent 工作区 |
| `public-tracker` | `none` | 公开的任务入口：`none`、`gh` 或 `linear` |
| `public-tracker-id` | — | 任务跟踪的标识，比如 GitHub 的 `owner/repo` |
| `beads.mode` | 配置了服务器主机时为 `server`，否则为 `embedded` | `embedded`、`server` 或 `none` |
| `beads.remote` | — | embedded 跟踪器的 Dolt remote |
| `beads.database` | 项目名 | 服务器上的数据库名 |
| `skills` | `[]` | 链接到这个项目工作区的技能 |
| `subagents` | `[]` | 在自带子 Agent 之外，只给这个项目用的子 Agent |

`public-tracker` 用来设置公开的任务入口和与贡献者的协作。它从不镜像私有的工作图，也不会把私有工作变成
公开任务；见 `triage-public` 技能。

::: info
`dotbrain refresh` 会逐字节保留项目声明。有意更新 Beads 配置时，会保留不相关的键、未知的嵌套值和显式的
空选择；这类显式更新可能会重新排版 YAML 注释。
:::

## `skills/skills.yaml`

你的全局技能，会链接到这台机器上的每个 Agent 会话。列出 `~/dotbrain/skills/` 下技能文件夹的路径：

```yaml
# ~/dotbrain/skills/skills.yaml
version: 1
targets:
  claude-code: ~/.claude/skills
  codex: ~/.codex/skills
global_extra:
  - my-collection/my-skill
  - another-collection        # select every descendant skill
```

包含 `SKILL.md` 的条目只选中这一个技能。否则，它的目录会递归展开为所有包含 `SKILL.md` 的子目录，
`node_modules` 除外。选中同一来源的重叠条目会去重。不同来源映射到同一个目标名时，会在任何链接或清理之前
失败；路径不存在或技能包为空也会失败。在选中的技能包里增删技能，下次同步时就会生效，不需要改这里的声明。

## `agents/agents.yaml`

分发到你个人 Agent 主目录的全局子 Agent。删除一个条目后，下次运行 `dotbrain agents link --scope global`
时会清理它对应的资源。

```yaml
# ~/dotbrain/agents/agents.yaml
# targets:
#   claude-code: ~/.claude/agents
#   codex: ~/.codex/agents
global:
  - some-shared-subagent
```

技能和 Claude Agent 定义是符号链接。Codex Agent 定义是可随时丢弃的真实 TOML 副本，带有归属标记
`# dotbrain-managed-agent: v1`；请编辑私有 `agents/` 目录下的源定义，而不是分发出去的副本。dotbrain 会迁移
自己的 Codex 符号链接，覆盖带标记的副本，保留没有标记的文件和其他来源的链接。如果和用户自己的文件重名，
会报告冲突，而不是替换。

运行时参数用 `--runtime claude|codex|all`。YAML 里的目标键仍然是 `claude-code` 和 `codex`。项目链接默认作用于
当前已连接的 checkout；`--scope global` 需要显式指定，并且不能和项目选择参数或 `--all` 一起用。
