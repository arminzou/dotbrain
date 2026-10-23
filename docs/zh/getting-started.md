# 快速开始

Dotbrain 以插件形式发布。先把它装进你的 Coding Agent，第一次使用时，插件的 `wire-brain` 技能会帮你
安装 CLI。按这条路走大约五分钟：

1. 安装插件。
2. 安装 CLI。
3. 连接仓库。
4. 备份并同步 dotbrain 主目录。
5. 验证结果。

| 需要 | 说明 |
| --- | --- |
| Claude Code 或 Codex | 任选其一，或两个都用。Hermes、OpenCode、Pi 和 Cursor 也可以用，见 [Hermes](#hermes)、[OpenCode](#opencode)、[Pi](#pi) 和 [Cursor](#cursor) |
| Git | dotbrain 主目录是一个 Git 仓库 |
| `uv` 和 `bd`（Beads） | 插件的安装脚本会帮你装 |
| 仅 Windows：开发人员模式 | 让 dotbrain 不需要管理员权限就能创建目录符号链接 |

## 开始之前 {#before-you-start}

- 不需要克隆本仓库，插件自带安装脚本。
- 按约定，dotbrain 把私有的项目状态放在 `~/dotbrain`（Windows 上是 `%USERPROFILE%\dotbrain`）。
  只有想换位置时才需要设置 `DOTBRAIN_HOME`。
- 被连接的代码仓库是公开还是私有，由它自己决定；dotbrain 会把 Brain 和执行状态放在仓库之外。

::: warning Windows
连接项目前请先开启[开发人员模式](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)，
这样 dotbrain 不需要管理员权限就能创建目录符号链接。
:::

## 1. 安装插件 {#_1-install-the-plugin}

与 Brain 配合的技能、dotbrain 约定和会话启动 hook 都以插件形式分发，所以每个 Agent 运行时
每台机器只装一次，不用每个仓库装一次。

::: code-group

```text [Claude Code]
/plugin marketplace add arminzou/dotbrain
/plugin install dotbrain@dotbrain
```

```bash [Codex]
codex plugin marketplace add arminzou/dotbrain
codex plugin add dotbrain@dotbrain
```

:::

在 Claude Code 中，这两行要分两次发送。

::: tip Codex 还需要多做一步
Codex 在你批准之前不会运行插件的 hook：启动 `codex`，打开 `/hooks`，信任 dotbrain 的几个 hook，
然后新开一个 thread。在此之前，技能可以加载，但会话开始时不会注入 Brain 上下文，dotbrain 主目录
也不会同步。Claude Code 装好插件后就会运行这些 hook。
:::

插件装在用户级别，所以它的技能在每个会话里都可用，包括还没连接的仓库。这也是为什么在连接任何
东西之前就能调用 `wire-brain`。

### Windows 上 `marketplace add` 失败怎么办 {#if-marketplace-add-fails-on-windows}

Claude Code 会把 marketplace 克隆到一个临时目录再重命名。在 Windows 上，如果 Defender 或搜索索引器
还占用着刚写入的文件，重命名可能以 `EBUSY` 或 `EPERM` 失败
（[claude-code#58241](https://github.com/anthropics/claude-code/issues/58241)）。重试一次就好，
文件被锁的时间很短。如果一直失败，就自己克隆 marketplace：

```bash
git clone https://github.com/arminzou/dotbrain \
  ~/.claude/plugins/marketplaces/dotbrain
```

然后照着 `~/.claude/plugins/known_marketplaces.json` 里已有条目的格式，为它加一条记录，
再重启 Claude Code。

## 2. 安装 CLI {#_2-get-the-cli}

插件负责分发技能和 Brain 上下文，`dotbrain` CLI 负责连接。两者需要分别安装。

**已经有 dotbrain 主目录了？** 如果你在别的机器上用过 dotbrain，你的 `~/dotbrain` 就是一个存着所有
Brainspace 的 git 仓库。先把它克隆下来，这样这台机器会用上已有的 Brain，而不是从一个空的开始：

```bash
git clone <your-remote> ~/dotbrain
```

`wire-brain` 找不到 dotbrain 主目录时也会问你这件事，但先克隆可以省一轮来回。

**让 Agent 来做。** 让它连接仓库，或者直接调用 `wire-brain`。这个技能会检查 `PATH` 上有没有
`dotbrain`；如果没有，就运行插件自带的安装脚本。脚本会提供 `uv`、`bd`（Beads）和与这个插件版本
锁定的 CLI，然后运行 `dotbrain bootstrap`。

**或者自己从 PyPI 安装。** 需要机器上已经有 `uv` 或 `pipx`：

::: code-group

```bash [uv]
uv tool install dotbrain
```

```bash [pipx]
pipx install dotbrain
```

:::

这只会安装 CLI，不会安装 `bd`（Beads），而 `dotbrain` 跟踪任务时要调用它。装完后运行
`dotbrain bootstrap`，再在连接项目之前运行 `dotbrain doctor --all` 检查机器是否就绪。
要连接带任务跟踪的项目，请先自己从 [Beads 仓库](https://github.com/gastownhall/beads)安装
`bd` 1.3.1 或更高版本。项目配置了任务跟踪之后，doctor 会检查它是否就绪。

**或者手动运行插件的安装脚本。** 如果缺少 `uv` 或 `bd`，它会帮你装好，再安装 CLI，不需要任何前置条件。
脚本在运行时的插件缓存里：

::: code-group

```bash [macOS / Linux]
~/.claude/plugins/cache/dotbrain/dotbrain/*/scripts/install.sh
```

```powershell [Windows]
pwsh -NoProfile -File "$env:USERPROFILE\.claude\plugins\cache\dotbrain\dotbrain\*\scripts\install.ps1"
```

:::

两个脚本都会在缺少时安装 `uv` 和 `bd`，安装锁定版本的 CLI，并运行 `dotbrain bootstrap`。
bootstrap 会用配置初始化全局的 dotbrain 主目录，并分发选定的全局技能和子 Agent。会话启动 hook
由插件提供。重复运行安装脚本是安全的。

本机首次运行 bootstrap 时，dotbrain 会限时运行 Hermes、OpenCode、Pi 和 Cursor 的 CLI
`--version` 命令（Cursor 用 `agent --version`），列出找到的每个运行时及其状态。命令失败或超时的
运行时会被跳过，其主目录不会被修改。stdin 和 stdout 都是终端时，会一次询问是否设置所有能运行的
运行时；按 Enter 接受，输入 `n` 则全部跳过，并给出逐个设置的命令。非交互运行或使用 `--json` 时，
会自动设置。结果会列出设置了哪些运行时，以及用于撤销的 `dotbrain detach --runtime <name>` 命令。

首次运行指本机既没有 bootstrap 完成标记，也没有这四个运行时的任何 dotbrain 交付副本。
克隆 dotbrain 主目录时不会带上本机缓存，因此新机器仍按首次运行处理。Bootstrap 会在被 gitignore
忽略的 `.cache/bootstrap-complete` 中记录完成状态，包括你拒绝设置或没有找到能运行的运行时的情况。
已有交付副本也算完成过设置。之后的 bootstrap 会更新已有交付；新发现的运行时只会提示
`dotbrain bootstrap --runtime <name>`，不会自动设置。用 `--runtime <name>` 可以精确选择要设置的
运行时，不会询问确认。Dotbrain 不保存退出列表。Detach 会保留完成标记，即使移除所有交付，
bootstrap 也不会再次自动设置。

::: warning
CLI 和插件要保持同一版本。插件的安装脚本会锁定匹配的 CLI 版本，只要让它来安装，两者就会保持一致。
:::

## 3. 连接仓库 {#_3-wire-a-repo}

在要连接的代码仓库里运行：

```bash
cd ~/repos/my-app
dotbrain wire
```

也可以在任意目录运行 `dotbrain wire --repo ~/repos/my-app`。

连接会为这个项目创建或修复一个私有的 Brainspace，并通过被 gitignore 的链接把仓库连过去。
仓库里会多出这些：

```mermaid
treeView-beta
  accTitle: What wiring adds to a code repo
  ~/repos/my-app/
    .brain ## link to the Brainspace's .brain/
    .beads ## link to the Brainspace's .beads/
    .claude/ ## skill and subagent links, individually ignored
    .codex/ ## skill links and generated agent files, individually ignored
```

[项目连接](wiring.md)逐项解释了这些条目。

## 4. 备份并同步 dotbrain 主目录 {#_4-back-up-and-sync-your-dotbrain-home}

`dotbrain bootstrap` 会把 `~/dotbrain` 初始化为 Git 仓库，但不会添加远程仓库。在你添加之前，
所有 Brain 都只存在一块硬盘上。在 GitHub、GitLab 或你自己的 Git 服务器上建一个空的**私有**仓库，
然后把主目录连上去：

```bash
cd ~/dotbrain
git status
git remote add origin <private-remote-url>
dotbrain sync
git push -u origin HEAD
```

先看一遍 `git status`：`dotbrain sync` 会提交所有没被 `~/dotbrain/.gitignore` 排除的文件。别把凭据
放进主目录。第一次 `dotbrain sync` 把这些文件记录为提交，`git push -u` 把它们推上去，并把这个远程
仓库设为当前分支的上游，之后的同步都从它拉取、向它推送。第二台机器也是通过这个远程仓库拿到你的
Brain：在连接任何东西之前，先[在那台机器上克隆它](#_2-get-the-cli)。

### 主目录同步 {#home-sync}

之后不用再手动提交和推送主目录。在已连接的仓库里，插件的 hook 会替你运行
[主目录同步](session-context.md#home-sync)：

- **会话开始时**，记录本地改动，拉取另一台机器的工作，然后推送。
- **Agent 每轮结束后**，只记录和推送，不拉取，这样文件不会在 Agent 运行时被改动。
- **会话结束时**，再做一次完整同步。

每个有改动的 Brainspace 单独一个提交，例如
`my-app: sync from LAPTOP (CONTEXT.md, designs/0004-x.md)`；Brainspace 之外的改动合成一个 `home`
提交。一个项目里没提交的改动，不会卡住另一个项目。你仍然可以自己写说明清楚的提交，同步只记录没人
提交的内容。想马上同步，手动运行 `dotbrain sync` 即可。

两台机器改了同一个文件的同一处时，同步会保留两个版本，`dotbrain doctor` 会列出多出来的那份。
见[冲突副本](troubleshooting.md#home-sync-left-a-conflict-copy)。

同步默认开启。要关闭它，在 [`config.yaml`](configuration.md#sync) 里设置 `sync.enabled: false`，
之后主目录要你自己提交和推送。

::: warning 从旧版本升级
升级后的第一个会话，会把主目录里所有没提交的内容提交并推送。已提交的内容也会被推送，所以升级前先
整理没提交的内容：想保留的，用你自己的提交信息提交；不能推送的，丢弃它、移出主目录，或加进
`~/dotbrain/.gitignore`；也可以先关闭同步。
:::

::: danger 远程仓库必须是私有的
远程仓库里有每个项目的 Brain，包括决策和设计。用公开仓库就等于把这些全部公开。
:::

::: warning 远程仓库里没有你的任务
Beads 任务跟踪的数据库被 `~/dotbrain/.gitignore` 忽略，所以推送只备份 Brain，不备份任务。
要备份或共享任务，请给项目配置 Dolt remote（`beads.remote`）或使用共享服务器。
详见 [Beads 后端](beads-backend.md)。
:::

## 5. 验证结果 {#_5-verify-the-result}

只读的健康检查：

```bash
dotbrain doctor
```

配置或插件改动后，修复生成的连接：

```bash
dotbrain refresh
```

到这一步，你应该有：

- 初始化好的 `~/dotbrain/config.yaml`
- `~/dotbrain/brainspaces/<name>/` 下的项目 Brainspace
- 仓库里指向这个 Brainspace 的本地连接
- 下一次 Agent 会话开始时注入的 Brain 上下文

最后一项要在连接好的仓库里新开一个会话来确认。Agent 应该不用你说，就已经知道项目的术语和既定决策。

## 保持更新 {#staying-current}

dotbrain 发布新版本时，插件和 CLI 要一起更新。

::: code-group

```text [Claude Code]
/plugin            # update dotbrain from the menu
/reload-plugins
```

```bash [Codex]
codex plugin marketplace upgrade
codex plugin add dotbrain@dotbrain
```

:::

然后让 CLI 跟上：可以让 Agent 来做，也可以用新版本号重新运行第 2 步的安装命令。

如果只想更新已发布的 CLI，用当初安装它的工具升级：

::: code-group

```bash [uv]
uv tool install dotbrain@latest
```

```bash [pipx]
pipx upgrade dotbrain
```

```bash [pip]
python -m pip install --upgrade dotbrain
```

:::

用 uv 时，请用 `dotbrain@latest`，不要用 `uv tool upgrade dotbrain`：锁定了版本的安装（比如插件
安装脚本装的那个）在 `uv tool upgrade` 下会停在原来的版本。

更新 CLI 不会更新插件，也不会更新私有的 dotbrain 数据。贡献者的 checkout 是 editable 安装，
用 Git 更新 checkout 即可。

插件和 CLI 都更新到匹配的版本后，运行 `dotbrain bootstrap` 更新本机资源，再运行
`dotbrain refresh --all` 更新已注册的项目。要回滚，就恢复之前的 CLI 和与之匹配的插件；用它维护
项目之前，先检查生成的约定有哪些变化。

### CLI 迁移 {#cli-migration}

CLI 现在使用统一的选择参数。旧的调用方式会直接报错，不再作为别名生效；请按下表更新已有脚本。

| 旧调用方式 | 新调用方式 |
| --- | --- |
| `--name <name>` | `--project <name>` |
| `--dotbrain <path>` | `--home <path>` |
| `--target claude-code` | `--runtime claude` |
| `--target codex` 或 `--target all` | `--runtime codex` 或 `--runtime all` |
| `beads load` | `beads sync` |
| `wire --all` | `refresh --all` |
| `--beads-server-host`、`--beads-server-port`、`--beads-server-user` | `--server-host`、`--server-port`、`--server-user` |
| `--beads-ssh-host`、`--beads-database`、`--beads-remote` | `--ssh-host`、`--database`、`--remote` |
| 隐式全局范围的资源链接 | `skills link --scope global` 或 `agents link --scope global` |
| `update` | 用安装 CLI 的包管理器升级 |
| `unwire --all` | 对每个项目运行 `unwire --project <name>` |
| unwire 的归档、删除或预览参数 | `unwire` 只负责断开；保留下来的目录用文件系统操作自己处理 |

隐藏的命令别名已经移除。不带参数的项目命令现在作用于当前已连接的 checkout；在它之外，请用
`--project` 选择项目。已有的配置键（比如 `targets.claude-code`）拼写不变。技能和 Claude 子 Agent
仍然是符号链接；Agent 同步时，会把 dotbrain 自己的 Codex Agent 符号链接迁移为带标记的真实文件，
并保留其他来源的条目。

JSON 结果中的严重级别 `advisory` 现在改为 `warning`，与已有的 warning 结果一致。匹配旧值的脚本
需要更新，因为旧值不会再输出。其他结果字段和退出码不变，只有 warning 时仍然以成功退出。
详见 [CLI 参考](cli-reference.md)。

## Claude Code 和 Codex 卸载 {#claude-codex-remove}

先退出运行时，再运行对应的命令：

```bash
dotbrain detach --runtime claude
dotbrain detach --runtime codex
```

这会移除默认 home 和已配置且存在的 profile home 里 dotbrain 创建的全局技能链接。
之后运行 bootstrap 仍会链接选中的 `global_extra` 技能；要停止向额外的 profile 交付，从
`skills/skills.yaml` 中移除该 profile。插件仍需通过 marketplace 卸载：Claude Code 使用
`/plugin uninstall dotbrain@dotbrain`，Codex 使用 `codex plugin remove dotbrain@dotbrain`。
项目 checkout 的连接不变；需要移除时，对每个 checkout 运行 `dotbrain unwire`。

## Hermes {#hermes}

Dotbrain 也支持 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 CLI。

::: warning 限制
- Hermes 用 Hermes CLI 测过。Hermes 的消息 gateway 没有测过。
- Dotbrain 不为 Hermes 提供子 Agent，所以 Hermes 没有原生的 dotbrain worker。在 `run-execution`
  里它只能当 lead。
- Hermes 只从你信任过的 checkout 加载项目技能。每个 checkout 都要单独信任，每个链接的 worktree 也一样。
- 只能手动调用的技能（比如 `dotbrain:run-retro`）会出现在 Hermes 的技能列表里，但模型加载不了。
  要用时自己输入 `/dotbrain:<skill>`。
- 移除 Hermes 的机器级交付，见[卸载](#hermes-remove)。
:::

### 安装 {#hermes-setup}

Hermes 没有 dotbrain 的 marketplace，插件由 CLI 复制到 Hermes 主目录。先安装 CLI（见[第 2 步](#_2-get-the-cli)），
然后运行：

```bash
dotbrain bootstrap
```

首次运行会询问是否设置 Hermes 及本机找到的其他能运行的运行时。只设置 Hermes，或之后再添加它，
请运行 `dotbrain bootstrap --runtime hermes`。

这会把插件复制到 `~/.hermes/plugins/dotbrain`（或 `$HERMES_HOME/plugins/dotbrain`），再运行
`hermes plugins enable dotbrain`。如果 `PATH` 里找不到 `hermes`，或者这条命令失败了，就自己运行
`hermes plugins enable dotbrain`。全新的 Hermes 主目录第一次运行 `hermes` 时要先准备运行环境，可能超过
一分钟，所以启用这一步可能会超时。

本机配置好 Hermes 后，新项目会自动启用它。项目如果已有显式的 `agents:` 列表，就在列表里加上
`hermes`。然后刷新技能链接，并信任这个 checkout：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
agents:
  - hermes
```

```bash
dotbrain refresh                   # 把选中的技能链接到 .hermes/skills/
hermes skills trust ~/repos/my-app
dotbrain doctor
```

插件副本缺失、过期或被禁用时，doctor 会报告；选了技能但没被信任的 checkout，doctor 也会报告。
装好后，在 checkout 里新开一个 Hermes 会话。打包的技能显示为 `dotbrain:<skill>`，你选的私有技能用它们自己的名字。

### Hermes 会话里会发生什么 {#hermes-sessions}

插件通过 Hermes 的 hook 执行同样的[主目录同步](session-context.md#home-sync)，并注入约定。详见
[Hermes 的运行时说明](session-context.md#runtime-notes)。

### 更新 {#hermes-update}

按[保持更新](#staying-current)升级 CLI，然后运行：

```bash
dotbrain bootstrap
dotbrain refresh --all
```

插件副本存在之后，不带参数的 `dotbrain bootstrap` 就会让它保持最新。Dotbrain 只替换它自己的副本，
不会动不是它创建的目录。新的 Hermes 会话会加载更新后的插件。

### 卸载 {#hermes-remove}

对单个 checkout，`dotbrain unwire` 会删掉它的 Hermes 技能链接。如果想保留连接、只去掉 Hermes，就从
`agents:` 里删掉 `hermes`，再手动删除 checkout 里 `.hermes/skills/` 下 dotbrain 创建的链接；
`dotbrain refresh` 不会删它们。然后撤销信任：

```bash
hermes skills untrust ~/repos/my-app
```

要移除 Hermes 的机器级交付，运行：

```bash
dotbrain detach --runtime hermes
```

这会移除 dotbrain 的插件副本和全局技能链接。Hermes 命令可用时，会先尝试禁用插件；禁用失败会显示警告，仍会继续移除。
不带参数的 bootstrap 不会再给 Hermes 交付；需要恢复时，
运行 `dotbrain bootstrap --runtime hermes`。

## OpenCode {#opencode}

Dotbrain 也支持 [OpenCode](https://opencode.ai) 的 CLI。

::: warning 限制
- OpenCode 用 OpenCode 1.18.35 测过，通过 `opencode run` 和 TUI。其他 OpenCode 版本，以及 OpenCode
  的桌面应用和 server 都没有测过。
- Dotbrain 不为 OpenCode 提供子 Agent，所以 OpenCode 没有原生的 dotbrain worker。在 `run-execution`
  里它只能当 lead。
- 如果你自己给 dotbrain 的技能建过链接或副本，先删掉。比如指向 dotbrain plugin 的
  `~/.config/opencode/skills` 链接，或者 `~/.claude/skills`、`~/.agents/skills` 下的副本。OpenCode
  也会读这些目录，遇到两个同名技能时会随机加载其中一个。`dotbrain doctor --verbose` 会列出每个重复的技能。
- OpenCode 不限制只能手动调用的技能（比如 `run-retro`）：它们照样出现在技能列表里，模型也可以自己调用。
- 移除 OpenCode 的机器级交付，见[卸载](#opencode-remove)。
:::

### 安装 {#opencode-setup}

OpenCode 没有 dotbrain 的 marketplace，plugin 由 CLI 复制到 OpenCode 的配置目录。先安装 CLI（见[第 2 步](#_2-get-the-cli)），
然后运行：

```bash
dotbrain bootstrap
```

首次运行会询问是否设置 OpenCode 及本机找到的其他能运行的运行时。只设置 OpenCode，或之后再添加它，
请运行 `dotbrain bootstrap --runtime opencode`。

这会把 plugin 复制到 `~/.config/opencode/plugins/dotbrain.js`，把打包的技能复制到
`~/.config/opencode/dotbrain/packaged/skills/`。在 Windows 上，`~` 指 `%USERPROFILE%`；设置了
`XDG_CONFIG_HOME` 时，目录改为 `$XDG_CONFIG_HOME/opencode`。你在 `skills/skills.yaml` 里选的全局技能会链接到
`~/.config/opencode/dotbrain/skills/`。Dotbrain 不改你的 OpenCode 配置文件：OpenCode 加载配置时，由 plugin 把这两个技能目录加进去。

plugin 运行的是 OpenCode 启动时 `PATH` 里的 `dotbrain`。找不到的话，会话照常可用，但没有约定，也不会同步。

本机配置好 OpenCode 后，新项目会自动启用它。项目如果已有显式的 `agents:` 列表，就在列表里加上
`opencode`。然后刷新技能链接：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
agents:
  - opencode
```

```bash
dotbrain refresh                   # 把选中的技能链接到 .opencode/skills/
dotbrain doctor
```

plugin 缺失、过期或不是 dotbrain 的，doctor 会报告；OpenCode 会找到两份的技能，doctor 也会报告。
装好后，在 checkout 里新开一个 OpenCode 会话。打包的技能用它们自己的名字，比如 `wire-brain`，不带
`dotbrain:` 前缀。你选的私有技能也用它们自己的名字。

链接技能会在 checkout 里创建 `.opencode/`。OpenCode 随后会在里面自己运行 `npm install`，生成
`package.json`、`node_modules/`，以及一个忽略这些文件的 `.gitignore`。Dotbrain 通过 `.git/info/exclude`
忽略它的技能链接，所以 `git status` 保持干净。

### OpenCode 会话里会发生什么 {#opencode-sessions}

plugin 通过 OpenCode 的 hook 执行同样的[主目录同步](session-context.md#home-sync)，并把约定加进 system prompt。详见
[OpenCode 的运行时说明](session-context.md#runtime-notes)。

### 更新 {#opencode-update}

按[保持更新](#staying-current)升级 CLI，然后运行：

```bash
dotbrain bootstrap
dotbrain refresh --all
```

plugin 文件存在之后，不带参数的 `dotbrain bootstrap` 就会让它和打包的技能保持最新。Dotbrain 只替换它自己标记过的文件。
OpenCode 在启动时加载 plugin，所以要重启 OpenCode 才能用上更新。

### 卸载 {#opencode-remove}

先退出 OpenCode，让退出时的同步跑完。

对单个 checkout，`dotbrain unwire` 会删掉它的 OpenCode 技能链接。如果想保留连接、只去掉 OpenCode，就从
`agents:` 里删掉 `opencode`，再手动删除 checkout 里 `.opencode/skills/` 下 dotbrain 创建的链接；
`dotbrain refresh` 不会删它们。`.opencode/` 里的其他文件属于 OpenCode，如果里面没有你
自己的东西，可以整个删掉。

要移除 OpenCode 的机器级交付，运行：

```bash
dotbrain detach --runtime opencode
```

这会移除 dotbrain 的插件文件、技能副本及全局技能链接，保留你自己的文件。之后重启 OpenCode。
不带参数的 bootstrap 不会再给 OpenCode 交付；需要恢复时，
运行 `dotbrain bootstrap --runtime opencode`。

## Pi {#pi}

Dotbrain 也支持 [Pi](https://github.com/earendil-works/pi) coding agent 的 CLI。

::: warning 限制
- Pi 用 Pi 1.4.0 测过。其他 Pi 版本都没有测过。
- Dotbrain 不为 Pi 提供子 Agent，所以 Pi 没有原生的 dotbrain worker。在 `run-execution` 里它只能当 lead。
- 只能手动调用的技能（比如 `run-retro`）对模型隐藏，只有你输入 `/skill:<name>` 时才会运行。但 Pi
  不会阻止模型直接读取这类技能的文件。
- 直接关掉控制台窗口很可能会跳过 Pi 的关闭事件，也就跳过了退出时的完整同步。每次运行后的推送照常进行，
  下次会话启动时的同步会补上剩下的部分。
- 移除 Pi 的机器级交付，见[卸载](#pi-remove)。
:::

### 安装 {#pi-setup}

Pi 没有 dotbrain 的 marketplace，扩展由 CLI 复制到 Pi 的 Agent 目录。先安装 CLI（见[第 2 步](#_2-get-the-cli)），
然后运行：

```bash
dotbrain bootstrap
```

首次运行会询问是否设置 Pi 及本机找到的其他能运行的运行时。只设置 Pi，或之后再添加它，
请运行 `dotbrain bootstrap --runtime pi`。

这会把扩展连同打包的技能复制到 `~/.pi/agent/extensions/dotbrain/`；设置了 `PI_CODING_AGENT_DIR` 时，
则复制到 `$PI_CODING_AGENT_DIR/extensions/dotbrain/`。在 Windows 上，`~` 指 `%USERPROFILE%`。你在
`skills/skills.yaml` 里选的全局技能会链接到 `~/.pi/agent/skills/`。Dotbrain 不会修改 Pi 的设置和信任文件。

扩展会运行 Pi 启动时 `PATH` 里找到的 `dotbrain`。找不到的话，会话照常可用，只是没有约定，也不会同步。

本机配置好 Pi 后，新项目会自动启用它。项目如果已有显式的 `agents:` 列表，就在列表里加上
`pi`。然后刷新技能链接：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
agents:
  - pi
```

```bash
dotbrain refresh                   # 把选中的技能链接到 .pi/skills/
dotbrain doctor
```

Pi 只从你信任的 checkout 里加载 `.pi/skills/`。在 checkout 里启动 `pi`，它询问是否信任这个项目时选择接受；
在此之前，`dotbrain doctor` 会警告项目技能只从受信任的 checkout 加载。打包的技能用自己的名字出现，比如
`wire-brain`，不带 `dotbrain:` 前缀。如果你自己有同名技能，Pi 用你的那个。

### Pi 会话里会发生什么 {#pi-sessions}

扩展通过 Pi 的事件执行同样的[主目录同步](session-context.md#home-sync)，并把约定加进 system prompt。详见
[Pi 的运行时说明](session-context.md#runtime-notes)。

### 更新 {#pi-update}

按[保持更新](#staying-current)升级 CLI，然后运行：

```bash
dotbrain bootstrap
dotbrain refresh --all
```

扩展存在之后，不带参数的 `dotbrain bootstrap` 就会让它和打包的技能保持最新。Dotbrain 只替换它自己标记过的扩展目录。
Pi 在启动时加载扩展，所以要重启 Pi 才能用上更新。

### 卸载 {#pi-remove}

先用 `/quit` 退出 Pi，让退出时的同步跑完。

对单个 checkout，`dotbrain unwire` 会删掉它的 Pi 技能链接。如果想保留连接、只去掉 Pi，就从 `agents:` 里删掉
`pi`，再手动删除 checkout 里 `.pi/skills/` 下 dotbrain 创建的链接；`dotbrain refresh` 不会删它们。

要移除 Pi 的机器级交付，运行：

```bash
dotbrain detach --runtime pi
```

这会移除 dotbrain 的扩展副本及全局技能链接，保留你自己的文件。之后重启 Pi。
不带参数的 bootstrap 不会再给 Pi 交付；需要恢复时，
运行 `dotbrain bootstrap --runtime pi`。

## Cursor {#cursor}

Dotbrain 也支持 [Cursor](https://cursor.com) 的 CLI。

::: warning 限制
- Cursor 用 Cursor CLI 2026.10.19 测过。其他 Cursor 版本和 Cursor 编辑器都没有测过。
- Dotbrain 不为 Cursor 提供子 Agent，所以 Cursor 没有原生的 dotbrain worker。在 `run-execution` 里它只能当 lead。
- Cursor 也会读取 checkout 和主目录里的 `.claude/skills`、`.codex/skills`、`.agents/skills` 和 `.grok/skills`。
  遇到两份同名但各自独立的技能时，它只用其中一份。`dotbrain doctor --verbose` 会列出 dotbrain 技能的每个重复。
- 恢复会话后，Cursor 保留会话开始时的约定，但不会运行启动同步。
- 直接关掉控制台窗口很可能会跳过 Cursor 的会话结束 hook，也就跳过了退出时的完整同步。每轮之后的推送照常进行，
  下次会话启动时的同步会补上剩下的部分。
- 移除 Cursor 的机器级交付，见[卸载](#cursor-remove)。
:::

### 安装 {#cursor-setup}

Cursor 没有 dotbrain 的 marketplace。先安装 CLI（见[第 2 步](#_2-get-the-cli)），然后运行：

```bash
dotbrain bootstrap
```

首次运行会询问是否设置 Cursor 及本机找到的其他能运行的运行时。只设置 Cursor，或之后再添加它，
请运行 `dotbrain bootstrap --runtime cursor`。

这会在 `~/.cursor/hooks.json` 里加入三个 dotbrain hook；文件不存在时会创建它，你自己的 hook 会保留。在 Windows 上，
`~` 指 `%USERPROFILE%`。如果你的 dotbrain Claude Code plugin 已安装、已启用且是最新的，Cursor 从它那里获取 dotbrain
打包的技能；否则使用 dotbrain 保存在 `~/dotbrain/.cache/cursor/` 里的副本。你在 `skills/skills.yaml` 里选的全局技能会
链接到 `~/.cursor/skills/`，Cursor 已经能在它读取的其他目录（比如 `~/.claude/skills`）里找到的除外。

hook 会运行 Cursor 启动时 `PATH` 里找到的 `dotbrain`。找不到的话，会话照常可用，只是没有约定，也不会同步。启用了
dotbrain Claude Code plugin 时，Cursor 也会加载它的 hook；dotbrain 让这些 hook 在 Cursor 下什么都不做，所以每个事件只运行一次。

本机配置好 Cursor 后，新项目会自动启用它。项目如果已有显式的 `agents:` 列表，就在列表里加上
`cursor`。然后刷新技能链接：

```yaml
# ~/dotbrain/brainspaces/<name>/.brain/project.yaml
agents:
  - cursor
```

```bash
dotbrain refresh                   # 把 Cursor 找不到的选中技能链接到 .cursor/skills/
dotbrain doctor
```

如果项目也声明了 `claude`，Cursor 通常会通过 `.claude/skills/` 找到技能，`.cursor/skills/` 会是空的。打包的技能用自己的
名字出现，比如 `wire-brain`。只能手动调用的技能（比如 `run-retro`）不会出现在 Cursor 的技能列表里，
需要你输入 `/<name>` 按名称调用。Cursor 不会阻止模型读取这些技能的 `SKILL.md` 文件。

### Cursor 会话里会发生什么 {#cursor-sessions}

hook 执行同样的[主目录同步](session-context.md#home-sync)，并把约定加进会话。详见
[Cursor 的运行时说明](session-context.md#runtime-notes)。

### 更新 {#cursor-update}

按[保持更新](#staying-current)升级 CLI，然后运行：

```bash
dotbrain bootstrap
dotbrain refresh --all
```

设置好 Cursor 之后，不带参数的 `dotbrain bootstrap` 就会让 hook 和打包技能的副本保持最新。Dotbrain 只替换它自己的 hook
条目和它自己的副本。开一个新的 Cursor 会话就能用上更新。

### 卸载 {#cursor-remove}

先退出 Cursor，让退出时的同步跑完。

对单个 checkout，`dotbrain unwire` 会删掉它的 Cursor 技能链接。如果想保留连接、只去掉 Cursor，就从 `agents:` 里删掉
`cursor`，再手动删除 checkout 里 `.cursor/skills/` 下 dotbrain 创建的链接；`dotbrain refresh` 不会删它们。

要移除 Cursor 的机器级交付，运行：

```bash
dotbrain detach --runtime cursor
```

这会移除 dotbrain 的用户 hook、技能副本和全局技能链接，保留其他条目。项目 checkout 的连接不变。
不带参数的 bootstrap 不会再给 Cursor 交付；需要恢复时，
运行 `dotbrain bootstrap --runtime cursor`。

## 需要时再改配置 {#edit-config-only-when-needed}

大多数首次配置都可以保持默认的 embedded beads 模式不动。

真需要配置时：

- [配置](configuration.md)介绍 `config.yaml` 和 `project.yaml`。
- [技能](skills.md)介绍技能的选择。

## 下一步 {#next}

- [工作流程](workflow.md)展示技能如何把工作从想法推进到结束设计。
- [架构](architecture.md)解释 Brainspace 模型。
- [故障排查与常见问题](troubleshooting.md)覆盖常见的安装问题。
