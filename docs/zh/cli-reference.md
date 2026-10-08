# CLI 参考

所有公开的 `dotbrain` 命令，按用途分组。任何命令加上 `--help`，都能在终端里看到同样的信息（英文）。

面向人的输出会按目标对改动和问题分组，把主目录路径缩写成 `~`，并用表格展示目录和项目信息。空列表、预览和
被跳过的操作都会明确显示。doctor 先显示问题和警告；用 `doctor -v` 可以包括所有健康的检查项。运行时激活状态和
会话的不确定性属于参考信息，只在 `doctor -v` 和 JSON 中显示，不算作通过的检查。缺失的已注册 hook 文件和失败的
插件检查仍然是警告。颜色会根据终端能力调整；重定向的输出保持纯文本。

一次性输出结果的命令支持 `--json`：stdout 包含一个结果，里面有命令、总体状态、每个目标的结果和错误。
问题的严重级别有 `info`、`warning` 和 `error`；只有 warning 时不算失败。退出码 `0` 表示成功，`1` 表示操作失败或
批量操作部分失败，`2` 表示调用或选择无效。

JSON 的使用方需要把对 `severity: advisory` 的判断改成 `severity: warning`。旧的严重级别不会再输出；其他结果字段和
退出码不变。

## 命令一览 {#commands-at-a-glance}

| 命令 | 作用 |
| --- | --- |
| [`bootstrap`](#dotbrain-bootstrap) | 为 dotbrain 准备这台机器：全局技能和子 Agent 链接。 |
| [`doctor`](#dotbrain-doctor) | 只读检查机器是否就绪以及所选项目的配置。 |
| [`wire`](#dotbrain-wire) | 创建 Brainspace 或连接一个 checkout，包括链接出来的 worktree。 |
| [`refresh`](#dotbrain-refresh) | 修复配置，同时保留项目声明和内容。 |
| [`unwire`](#dotbrain-unwire) | 断开一个 checkout，保留它的 Brainspace 和任务跟踪数据库。 |
| [`projects list`](#dotbrain-projects-list) | 根据本地声明和连接，列出所有已注册的项目。 |
| [`projects show`](#dotbrain-projects-show) | 查看当前已连接的项目，或某个指定项目已注册的 checkout。 |
| [`skills list`](#dotbrain-skills-list) | 查找本地可用的技能。 |
| [`skills link`](#dotbrain-skills-link) | 在项目范围或显式的全局范围内同步选定的技能。 |
| [`agents list`](#dotbrain-agents-list) | 查找本地可用的 Agent。 |
| [`agents link`](#dotbrain-agents-link) | 在项目范围或显式的全局范围内同步选定的 Agent。 |
| [`beads sync`](#dotbrain-beads-sync) | 同步声明的本地任务跟踪绑定，拉取已配置的 remote；从不推送。 |
| [`beads migrate`](#dotbrain-beads-migrate) | 把 embedded 跟踪器迁移到服务器，保留历史和用于回滚的备份。 |
| [`beads list-db`](#dotbrain-beads-list-db) | 列出远程数据库标识，包括没有对应 Brainspace 的数据库。 |
| [`beads drop-db`](#dotbrain-beads-drop-db) | 显式删除一个远程数据库；从不根据当前项目推断。 |
| [`site init`](#dotbrain-site-init) | 为 Brain 创建站点：生成 .brain/site/，包含 site.yaml、首页和使用手册。 |
| [`site dev`](#dotbrain-site-dev) | 在本地（127.0.0.1）运行 Brain 站点，带热更新。 |
| [`site build`](#dotbrain-site-build) | 构建 Brain 站点；导航链接到不存在的页面时失败。 |
| [`site preview`](#dotbrain-site-preview) | 在本地（127.0.0.1）运行上一次的构建结果。 |
| [`hook session-start`](#dotbrain-hook-session-start) | 输出已连接仓库的 Brain 上下文。 |

## 配置 {#setup}

准备机器并检查它的状态。见[快速开始](getting-started.md)。

### `dotbrain bootstrap` {#dotbrain-bootstrap}

为 dotbrain 准备这台机器：全局技能和子 Agent 链接。

```text
dotbrain bootstrap [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain doctor` {#dotbrain-doctor}

只读检查机器是否就绪以及所选项目的配置。

```text
dotbrain doctor [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--all` | — | 检查所有已注册的项目。 |
| `--verbose`, `-v` | — | 包括健康的检查项和参考信息。 |
| `--json` | — | 输出一个结构化结果。 |

## 项目 {#projects}

把代码仓库连接到 Brainspace 并保持同步。见[项目连接](wiring.md)。

### `dotbrain wire` {#dotbrain-wire}

创建 Brainspace 或连接一个 checkout，包括链接出来的 worktree。

```text
dotbrain wire [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--repo` *path* | — | 要连接的 checkout；默认是当前的 Git checkout。 |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--no-repo` | — | 创建只有 Brain 的项目；需要 `--project`。 |
| `--skip-beads` | — | 创建时不带任务跟踪。 |
| `--remote` *text* | — | 首次创建任务跟踪时使用的 Dolt remote。 |
| `--server-host` *text* | — | Dolt 服务器主机；默认取自配置。 |
| `--server-port` *text* | — | Dolt 服务器端口；默认取自配置。 |
| `--server-user` *text* | — | Dolt 服务器用户；默认取自配置。 |
| `--database` *text* | — | 任务跟踪数据库；默认是项目名。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain refresh` {#dotbrain-refresh}

修复配置，同时保留项目声明和内容。

```text
dotbrain refresh [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--all` | — | 刷新所有已注册的项目。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain unwire` {#dotbrain-unwire}

断开一个 checkout，保留它的 Brainspace 和任务跟踪数据库。

```text
dotbrain unwire [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--repo` *path* | — | 要断开的 checkout。 |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain projects list` {#dotbrain-projects-list}

根据本地声明和连接，列出所有已注册的项目。

```text
dotbrain projects list [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain projects show` {#dotbrain-projects-show}

查看当前已连接的项目，或某个指定项目已注册的 checkout。

```text
dotbrain projects show [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

## 技能和 Agent {#skills-and-agents}

把技能和运行时原生的子 Agent 链接到 Agent 运行时。见[技能](skills.md)。

### `dotbrain skills list` {#dotbrain-skills-list}

查找本地可用的技能。

```text
dotbrain skills list [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--project` *text* | — | 显示某个指定 Brainspace 的选择。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain skills link` {#dotbrain-skills-link}

在项目范围或显式的全局范围内同步选定的技能。

```text
dotbrain skills link [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--scope` *text* | `project` | 分发范围：project 或 global。 |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--repo` *path* | — | 选择一个已连接的 checkout；默认是当前 checkout。 |
| `--all` | — | 同步所有已注册的项目。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain agents list` {#dotbrain-agents-list}

查找本地可用的 Agent。

```text
dotbrain agents list [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--project` *text* | — | 显示某个指定 Brainspace 的选择。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain agents link` {#dotbrain-agents-link}

在项目范围或显式的全局范围内同步选定的 Agent。

```text
dotbrain agents link [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--runtime` *text* | `all` | 过滤运行时：claude、codex 或 all。 |
| `--scope` *text* | `project` | 分发范围：project 或 global。 |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--repo` *path* | — | 选择一个已连接的 checkout；默认是当前 checkout。 |
| `--all` | — | 同步所有已注册的项目。 |
| `--json` | — | 输出一个结构化结果。 |

## Beads {#beads}

管理 Beads 任务跟踪的状态和后端。见 [Beads 后端](beads-backend.md)。

### `dotbrain beads sync` {#dotbrain-beads-sync}

同步声明的本地任务跟踪绑定，拉取已配置的 remote；从不推送。

```text
dotbrain beads sync [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--all` | — | 同步所有已注册的项目。 |
| `--dry-run` | — | 预览任务跟踪同步和已配置的拉取。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain beads migrate` {#dotbrain-beads-migrate}

把 embedded 跟踪器迁移到服务器，保留历史和用于回滚的备份。

```text
dotbrain beads migrate [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--all` | — | 迁移所有已注册的项目。 |
| `--server-host` *text* | — | 目标 Dolt 服务器主机；默认取自配置。 |
| `--server-port` *text* | — | 目标 Dolt 服务器端口；默认取自配置。 |
| `--server-user` *text* | — | 目标 Dolt 服务器用户；默认取自配置。 |
| `--database` *text* | — | 单个项目的数据库覆盖。 |
| `--dry-run` | — | 预览保留历史的迁移。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain beads list-db` {#dotbrain-beads-list-db}

列出远程数据库标识，包括没有对应 Brainspace 的数据库。

```text
dotbrain beads list-db [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--server-host` *text* | — | Dolt 服务器主机；默认取自配置。 |
| `--server-port` *text* | — | Dolt 服务器端口；默认取自配置。 |
| `--server-user` *text* | — | Dolt 服务器用户；默认取自配置。 |
| `--ssh-host` *text* | — | 可选的 SSH 跳板；默认取自配置。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain beads drop-db` {#dotbrain-beads-drop-db}

显式删除一个远程数据库；从不根据当前项目推断。

```text
dotbrain beads drop-db [OPTIONS] NAME
```

| 参数 | 说明 |
| --- | --- |
| `NAME` | 数据库标识，包括孤立的数据库。 |

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--yes` | — | 确认这次破坏性的删除。 |
| `--dry-run` | — | 只预览，不删除。 |
| `--server-host` *text* | — | Dolt 服务器主机；默认取自配置。 |
| `--server-port` *text* | — | Dolt 服务器端口；默认取自配置。 |
| `--server-user` *text* | — | Dolt 服务器用户；默认取自配置。 |
| `--ssh-host` *text* | — | 可选的 SSH 跳板；默认取自配置。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

## Brain 站点 {#brain-site}

创建和运行 Brain 的私有站点。见 [Brain 站点](brain-site.md)。

### `dotbrain site init` {#dotbrain-site-init}

为 Brain 创建站点：生成 .brain/site/，包含 site.yaml、首页和使用手册。

```text
dotbrain site init [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--title` *text* | — | 站点标题。默认是 '&lt;name&gt; Brain'。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain site dev` {#dotbrain-site-dev}

在本地（127.0.0.1）运行 Brain 站点，带热更新。

```text
dotbrain site dev [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--home` *path* | — | 覆盖私有数据目录。 |

### `dotbrain site build` {#dotbrain-site-build}

构建 Brain 站点；导航链接到不存在的页面时失败。

```text
dotbrain site build [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--home` *path* | — | 覆盖私有数据目录。 |
| `--json` | — | 输出一个结构化结果。 |

### `dotbrain site preview` {#dotbrain-site-preview}

在本地（127.0.0.1）运行上一次的构建结果。

```text
dotbrain site preview [OPTIONS]
```

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `--project` *text* | — | 选择一个指定的 Brainspace。 |
| `--home` *path* | — | 覆盖私有数据目录。 |

## 内部命令 {#internal}

由插件的 hook 运行，不需要手动运行。见[会话上下文](session-context.md)。

### `dotbrain hook session-start` {#dotbrain-hook-session-start}

输出已连接仓库的 Brain 上下文。失败时放行：没有上下文时不输出，以 0 退出。

```text
dotbrain hook session-start [ARGS]
```

| 参数 | 说明 |
| --- | --- |
| `ARGS` | — |
