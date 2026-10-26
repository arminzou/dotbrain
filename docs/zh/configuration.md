# 配置

大多数情况下都不需要改配置。真要改时，一共只有两个文件，都在你私有的 dotbrain 主目录里：一个管本机，一个管单个项目。

```mermaid
treeView-beta
  accTitle: Where dotbrain's configuration files live
  ~/dotbrain/
    config.yaml ## machine: every global setting
    skills/ ## your skill sources
    subagents/ ## your custom subagent sources
    brainspaces/
      my-app/
        .brain/
          project.yaml ## one project
```

| 文件 | 范围 | 由谁初始化 |
| --- | --- | --- |
| `~/dotbrain/config.yaml` | 本机：基础设施、运行时 profiles、全局技能和子 Agent | `dotbrain bootstrap` |
| `brainspaces/<name>/.brain/project.yaml` | 单个项目 | `dotbrain wire` |

修改项目声明后，运行 `dotbrain refresh`（或 `dotbrain refresh --all`）。全局资源的变化用
`dotbrain skills link --scope global` 或 `dotbrain agents link --scope global` 同步。

## 环境变量 {#environment}

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DOTBRAIN_HOME` | `~/dotbrain`（Windows 上是 `%USERPROFILE%\dotbrain`） | Brainspace 和配置存放的位置 |
| `HERMES_HOME` | `~/.hermes` | Hermes 自己的主目录；dotbrain 把 Hermes 插件副本和 Hermes 全局技能放在这里 |
| `XDG_CONFIG_HOME` | `~/.config` | OpenCode 配置目录的上一级；dotbrain 把 OpenCode plugin 文件、打包的技能和 OpenCode 全局技能放在 `$XDG_CONFIG_HOME/opencode` 下 |
| `PI_CODING_AGENT_DIR` | `~/.pi/agent` | Pi 的 Agent 目录；dotbrain 把 Pi 扩展副本和 Pi 全局技能放在这里 |

## `config.yaml`

所有全局设置都在这里：[server 模式](beads-backend.md#server-mode)的 Beads、[主目录同步](#sync)、
额外的运行时主目录，以及分发到你个人 Agent 主目录的技能和子 Agent。初始化出来的文件里，这些段落都是注释掉的。

```yaml
# ~/dotbrain/config.yaml
version: 4

beads:
  server:
    host: db.example.internal
    port: "3307"
    user: beads
    ssh_host: bastion.example.internal   # optional SSH hop, used by beads drop-db

profiles:                     # extra Claude Code and Codex homes
  claude-code: [~/.claude-work]
  codex: [~/.codex-work]

skills:                       # global skills, under ~/dotbrain/skills/
  - my-collection/my-skill
  - another-collection        # select every descendant skill

subagents:                    # custom subagents, under ~/dotbrain/subagents/
  - some-shared-subagent
```

::: warning
不要把凭据写进 `config.yaml`，请放在你的密钥存储里。
:::

### `sync:` {#sync}

[主目录同步](session-context.md#home-sync)把 dotbrain 主目录里没提交的改动记录为提交，再和主目录的
远程仓库交换。没有这一段时，同步是开启的。只有要关闭同步或调整大小上限时，才需要加上它：

```yaml
# ~/dotbrain/config.yaml
sync:
  enabled: false        # default true
  max-file-size: 5MB    # default 1MB
```

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `sync.enabled` | `true` | 设为 `false` 会关闭 hook 里的同步和 `dotbrain sync`，主目录要你自己提交和推送 |
| `sync.max-file-size` | `1MB` | 超过这个大小的文件不会提交，并会被报告。可以写字节数，如 `1048576`；也可以写 `500KB`、`1MB`、`2GB` 这样的大小（1 KB = 1024 字节） |

远程仓库就是主目录当前分支的上游，没有单独的配置项。`config.yaml` 通过这个远程仓库在所有机器间共享，
所以设置对每台机器都生效。同步在提交信息里用主机名标出是哪台机器。

## `project.yaml`

项目的身份，以及与全局默认值不同的地方。一个使用 server 模式 Beads、额外加了一个技能的项目是这样的：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
execution-engine: beads

# 省略 agents 则跟随本机配置；显式列表只启用所列项。
agents:            # claude, codex, hermes, opencode, pi, cursor
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
| `agents` | 本机已配置的 runtime | Claude、Codex 按 CLI 是否在 PATH 上判断；[`hermes`](getting-started.md#hermes)、[`opencode`](getting-started.md#opencode)、[`pi`](getting-started.md#pi)、[`cursor`](getting-started.md#cursor) 按 dotbrain 自己分发的副本是否存在判断。显式列表只启用所列项；`[]` 全部禁用。新项目默认注释掉此键，已有列表保持不变。 |
| `public-tracker` | `none` | 公开的任务入口：`none`、`gh` 或 `linear` |
| `public-tracker-id` | — | 任务跟踪的标识，比如 GitHub 的 `owner/repo` |
| `beads.mode` | 配置了服务器主机时为 `server`，否则为 `embedded` | `embedded`、`server` 或 `none` |
| `beads.remote` | — | embedded 跟踪器的 Dolt remote |
| `beads.database` | 项目名 | 服务器上的数据库名 |
| `skills` | `[]` | 链接到这个项目工作区的技能 |
| `subagents` | `[]` | 在自带子 Agent 之外，只给这个项目用的子 Agent |
| `retro.promotion.auto-deliver` | `false` | 由 skill 读取：允许自动提交、推送规则提案并创建 PR |
| `retro.promotion.destinations` | `[]` | 允许修改的已有公开指南，相对仓库的路径数组；启用自动交付时不能为空 |

刷新时，已存在但不在 `agents` 解析结果中的工作区会触发警告，里面的文件和链接都保持不变。

Codex 项目技能使用 `<checkout>/.agents/skills/`，配置和子 Agent 仍在 `.codex/` 下。全局技能和
profile 主目录的位置不变。旧链接迁移和冲突处理见[技能同步](skills.md#select-and-reconcile-skills)。

`public-tracker` 用来设置公开的任务入口和与贡献者的协作。它从不镜像私有的工作图，也不会把私有工作变成
公开任务；见 `triage-public` 技能。

`run-retro` 直接读取这些设置，不增加 CLI 交付命令。自动交付未设置或关闭时，它更新私有发现，
查找仓库已有的规则、标准或贡献指南，并建议文件位置和规则，由你决定是否创建 PR。
你可以单独授权某个提案，也可以在确认仓库接受该位置后启用自动交付：

```yaml
# project.yaml — 先确认这个仓库接受该位置，再启用
retro:
  promotion:
    auto-deliver: true
    destinations:
      - CONTRIBUTING.md
      - docs/code-standards.md
```

各目标文件必须已存在于仓库内。skill 按发现的主题和适用范围选择最合适的文件，不把同一规则复制到所有文件。
没有合适位置或归属不清时，它会建议位置，由你决定。新建规则文件需要明确同意；skill 不会默认要求仓库采用 `RULES.md`。
PR 批准与合并仍由你决定。关闭自动交付后，私有记录和只读的合并状态核对照常进行。

::: info
`dotbrain refresh` 会逐字节保留项目声明。有意更新 Beads 配置时，会保留不相关的键、未知的嵌套值和显式的
空选择；这类显式更新可能会重新排版 YAML 注释。
:::

## 全局技能和 profiles {#global-skills}

`skills:` 列出你的全局技能，它们会链接到这台机器上的每个 Agent 会话。每一项是 `~/dotbrain/skills/`
下某个技能文件夹的路径。

Claude Code 和 Codex 的技能会链接到默认主目录（`~/.claude` 和 `~/.codex`）及 `profiles` 中每个额外
主目录下的 `skills/`。本机不存在的 profile 主目录会静默跳过，方便多台机器共享此文件。其他运行时继续
沿用各自的路径重定位变量和插件安装方式，不接受 profiles。

位于已连接 checkout 或 worktree 内的主目录会被拒绝，其中的链接不会被改动；主目录及其上级目录可以是
符号链接。Doctor 还会检查每个 Claude Code 主目录是否安装了 dotbrain 插件。

包含 `SKILL.md` 的条目只选中这一个技能。否则，它的目录会递归展开为所有包含 `SKILL.md` 的子目录，
`node_modules` 除外。选中同一来源的重叠条目会去重。不同来源映射到同一个目标名时，会在任何链接或清理之前
失败；路径不存在或技能包为空也会失败。在选中的技能包里增删技能，下次同步时就会生效，不需要改这里的声明。

## 全局子 Agent {#global-subagents}

`subagents:` 列出分发到你个人 Agent 主目录的自定义子 Agent。每个名字对应
`~/dotbrain/subagents/claude/<name>.md` 或 `~/dotbrain/subagents/codex/<name>.toml` 下的源文件。
删除一个条目后，下次运行 `dotbrain agents link --scope global` 时会清理它对应的资源。

打包的子 Agent（`worker`、`researcher`、`reviewer`、`verifier`）没有全局范围，请按项目选择。
写在这里的打包名称会被跳过，doctor 也会报告。

Claude Code 和 Codex 会把 Agent 分发到默认主目录和同一组 `profiles` 下的 `agents/`。不存在的 profile
会跳过；位于已连接 checkout 内的目标会报错并跳过。

技能和 Claude Agent 定义是符号链接。Codex Agent 定义是可随时丢弃的真实 TOML 副本，带有归属标记
`# dotbrain-managed-agent: v1`；请编辑 `~/dotbrain/subagents/` 下的源定义，而不是分发出去的副本。dotbrain 会迁移
自己的 Codex 符号链接，覆盖带标记的副本，保留没有标记的文件和其他来源的链接。如果和用户自己的文件重名，
会报告冲突，而不是替换。

运行时参数用 `--runtime claude|codex|hermes|opencode|pi|cursor|all`。profiles 的键是 `claude-code` 和 `codex`；
Hermes、OpenCode、Pi 和 Cursor 不接收子 Agent。项目链接默认作用于当前已连接的 checkout；`--scope global`
需要显式指定，并且不能和项目选择参数或 `--all` 一起用。

## 从旧版本升级 {#upgrading}

以前的全局设置分散在三个文件里。升级后第一次运行 `dotbrain bootstrap`，会把它们合并进 `config.yaml` version 4：

| 之前 | 之后 |
| --- | --- |
| `config.yaml` version 3 | `config.yaml` version 4；`beads` 和 `sync` 不变 |
| `skills/skills.yaml` 的 `profiles` | `config.yaml` 的 `profiles` |
| `skills/skills.yaml` 的 `global_extra`（或 `extra`） | `config.yaml` 的 `skills` |
| `agents/agents.yaml` 的 `global` | `config.yaml` 的 `subagents`，只保留自定义子 Agent |
| `agents/agents.yaml` 的 `global` 里的打包名称 | 删除并报告；打包子 Agent 请按项目选择 |
| 指向运行时默认位置的 `targets`，例如 `~/.claude/skills` 或 `~/.hermes/skills` | 删除 |
| 指向自定义目录的 `targets`，例如 `~/.codex-work/skills` | 父目录变成 profile 主目录，例如 `codex: [~/.codex-work]` |
| `~/dotbrain/agents/` | `~/dotbrain/subagents/`，只放自定义子 Agent 的源文件 |

Bootstrap 先把原文件备份到 `~/dotbrain/.cache/config-backups/`，再写入合并后的 `config.yaml`，删除
`skills/skills.yaml` 和 `agents/agents.yaml`，并逐项报告。如果某一步失败（比如文件被占用），旧文件会放回原处，
下次 bootstrap 会重试。各运行时主目录里指向 `agents/` 的 Claude Code 链接会改指向 `subagents/`，即使这次只为一个运行时运行 bootstrap。profile 会同时接收技能和子 Agent，所以由 target
转换来的主目录也可能开始接收子 Agent。再次运行不会有任何改动。需要恢复时，从报告里的备份目录还原文件。

无法安全合并时，bootstrap 会停下来，不改任何文件。这些情况包括：YAML 无法解析；使用了锚点、合并键或标签；
有重复或未知的键；某个值和 `config.yaml` 里已有的值冲突；Claude Code 和 Codex 以外运行时的自定义 target；
`agents/` 和 `subagents/` 里都有文件。修好报告里的文件后再运行一次 bootstrap。在那之前，全局分发会暂停，
doctor 会报告遗留的文件。迁移完成后，dotbrain 不会再读取旧文件。
