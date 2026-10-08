# 快速开始

Dotbrain 以插件形式发布。先把它装进你的 Coding Agent，第一次使用时，插件的 `wire-brain` 技能会帮你
安装 CLI。按这条路走大约五分钟：

1. 安装插件。
2. 安装 CLI。
3. 连接仓库。
4. 备份 dotbrain 主目录。
5. 验证结果。

| 需要 | 说明 |
| --- | --- |
| Claude Code 或 Codex | 任选其一，或两个都用 |
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
Codex 在你批准之前不会运行插件的 hook：启动 `codex`，打开 `/hooks`，信任 dotbrain 的 hook，
然后新开一个 thread。在此之前，技能可以加载，但会话开始时不会注入 Brain 上下文。
Claude Code 装好插件后就会运行 hook。
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

## 4. 备份 dotbrain 主目录 {#_4-back-up-your-dotbrain-home}

`dotbrain bootstrap` 会把 `~/dotbrain` 初始化为 Git 仓库，但不会添加远程仓库。在你添加之前，
所有 Brain 都只存在一块硬盘上。在 GitHub、GitLab 或你自己的 Git 服务器上建一个空的**私有**仓库，
然后推送：

```bash
cd ~/dotbrain
git status
git add .
git commit -m "Back up dotbrain home"
git remote add origin <private-remote-url>
git push -u origin HEAD
```

暂存之前先检查文件，别把凭据放进 Git。bootstrap 初始化仓库时不会创建提交，所以第一次推送需要上面
这次提交。之后 Brain 有改动时，暂存并提交想保留的改动，再推送即可。第二台机器也是通过这个远程仓库
拿到你的 Brain：在连接任何东西之前，先[在那台机器上克隆它](#_2-get-the-cli)。

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

## 需要时再改配置 {#edit-config-only-when-needed}

大多数首次配置都可以保持默认的 embedded beads 模式不动。

真需要配置时：

- [配置](configuration.md)介绍 `config.yaml` 和 `project.yaml`。
- [技能](skills.md)介绍技能的选择。

## 下一步 {#next}

- [工作流程](workflow.md)展示技能如何把工作从想法推进到结束设计。
- [架构](architecture.md)解释 Brainspace 模型。
- [故障排查与常见问题](troubleshooting.md)覆盖常见的安装问题。
