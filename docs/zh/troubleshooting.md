# 故障排查与常见问题

排查任何问题都先运行只读的健康检查。它会报告机器是否就绪、项目连接情况和 Beads 状态的偏差，不会改动任何东西：

```bash
dotbrain doctor
```

doctor 还会检查以下三种偏差并给出警告：

- CLI 和已注册的 Claude Code 插件版本不一致：把两者升级到相同版本。
- Brain 的 `DOTBRAIN.md` 与 CLI 自带的约定不同：运行 `dotbrain refresh`。
- 设计仍为 `lifecycle: active`，但通过 `spec: design:<文件名去掉扩展名>` 关联的 epic 已全部关闭：
  运行 `close-design` 或修正 lifecycle。

这些检查只读取数据。缺少插件 registry、约定文件或 tracker 数据时，doctor 会跳过检查，
在 `--verbose` 和 JSON 输出中说明原因。这些警告不影响退出码。

## 常见问题 {#common-problems}

### Agent 不了解项目 {#the-agent-does-not-know-the-project}

会话开始时没有加载 dotbrain 约定。

1. 确认仓库已连接：仓库根目录应该有 `.brain`，并且指向一个目录。
2. 确认 Agent 的 shell 能在 `PATH` 上找到 CLI：`dotbrain --version`。找不到 `dotbrain` 时，hook 不会有任何输出。
3. **Codex：** 在 `/hooks` 里信任 dotbrain 的几个 hook，然后新开一个 thread。
4. 新开一个会话。hook 在会话开始时运行，不会在会话中途运行。

### `.brain` 或 `.beads` 缺失或失效 {#brain-or-beads-is-missing-or-dangling}

::: code-group

```bash [主 checkout]
dotbrain refresh        # repair links in an already-wired repo
dotbrain wire           # or reconnect from scratch
```

```bash [Git worktree]
dotbrain wire           # attach through the main checkout's existing wiring
dotbrain refresh        # maintain the current wired worktree
```

:::

worktree 使用主 checkout 的 Brain。CLI 通过 Git 元数据找到主 checkout，并分发本地运行时资源。
`.claude` 和 `.codex` 里的资源请用 CLI 来同步。

### Windows 上创建符号链接失败 {#symlink-creation-fails-on-windows}

开启[开发人员模式](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development)，
让普通用户也能创建目录符号链接，然后重新运行 `dotbrain wire`。

### Windows 上 `marketplace add` 报 `EBUSY` 或 `EPERM` {#marketplace-add-fails-with-ebusy-or-eperm-on-windows}

Defender 或搜索索引器占用着刚克隆的文件。重试一次。如果一直失败，请按[手动克隆步骤](getting-started.md#if-marketplace-add-fails-on-windows)操作。

### `bd: command not found`

`uv tool install dotbrain` 只安装 CLI。请从[它的仓库](https://github.com/gastownhall/beads)安装 Beads，
或者运行插件的安装脚本，它会把两者都装好。

### 插件和 CLI 版本不一致 {#the-plugin-and-cli-versions-disagree}

按[保持更新](getting-started.md#staying-current)里的说明，两者一起更新。CLI 用哪个包管理器装的，就用它的升级命令。

### Pi 看不到项目的技能 {#pi-does-not-see-project-skills}

在 Pi 信任这个 checkout 之前，`dotbrain doctor` 会警告 `project skills load only from a trusted checkout`。
在 checkout 里启动 `pi` 并接受信任提示即可。详见[Pi](getting-started.md#pi)。

### OpenCode 加载了另一份技能 {#opencode-loads-a-different-copy-of-a-skill}

如果 OpenCode 会找到同一个 dotbrain 技能的两份：一份来自 dotbrain，一份来自你自己的目录（比如
`~/.config/opencode/skills` 链接或 `~/.claude/skills`），`dotbrain doctor --verbose` 会报告
`OpenCode loads one of the two at random`。删掉另一份，或者把它移出 OpenCode 的技能目录，然后重启 OpenCode。
详见[OpenCode](getting-started.md#opencode)。

### `dotbrain site` 失败 {#dotbrain-site-fails}

检查 `node --version`；站点需要 Node.js 22.12 或更高版本。顺着构建错误找到提到的文件和行：缺失的链接、
无效的 frontmatter、格式错误的 HTML 或 Vue 标记都可能导致构建失败。遇到 "Element is missing end tag" 时，
找一找没加反引号的占位符，比如 `<name>` 或 `<path>`，用行内代码包起来，表格里也一样。见
[Brain 站点配置](brain-site-configuration.md#what-fails-the-build)。

## 主目录同步 {#home-sync}

`dotbrain doctor` 根据本地 Git 数据报告[主目录同步](session-context.md#home-sync)的状态。它不会
fetch，也不会改动任何东西。

### 同步留下了冲突副本 {#home-sync-left-a-conflict-copy}

doctor 报告 `home sync: open conflict copy <path>`。

两台机器在同步之前改了同一个文件的同一处。同步保留了两个版本：

- 这台机器的版本留在原处，文件名不变。
- 另一台机器的版本存到旁边，名为 `<stem>.sync-conflict-<date>-<host>` 加上原来的扩展名，例如
  `CONTEXT.sync-conflict-2026-10-20-LAPTOP.md`。这里的主机名是执行合并、写出副本的那台机器，
  不是副本内容来自的机器。同一天同一个文件再次冲突时，会加上编号，如 `-2`。

同步不会替你合并。打开两个文件，把要保留的内容合并进原文件，然后删掉副本。下一次同步会记录这两处
改动，另一台机器上的副本也会随之消失。Brain 站点会跳过冲突副本，所以它们不会变成多余的页面。

### 有文件一直没提交 {#a-file-stays-uncommitted}

doctor 报告 `home sync: <path> is over the size limit and stays uncommitted`。

同步从不提交大于 `sync.max-file-size`（默认 1 MB）的文件。任选一种处理方式：

- 如果它该放在 `~/dotbrain` 里，自己提交它。
- 把它加进 `~/dotbrain/.gitignore`。
- 在 [`config.yaml`](configuration.md#sync) 里调高上限。

`dotbrain sync` 还会对主目录里嵌套的 Git 仓库发出警告。同步永远不会记录它们。

### 传入的改动碰到了未提交的文件 {#incoming-changes-touch-an-uncommitted-file}

`dotbrain sync` 失败并报告 `did not integrate <upstream>; nothing was pushed`，后面附上 Git 的原始诊断信息。

另一台机器改动或新增了文件，传入的内容会覆盖未提交或被忽略的本地文件。这也可能涉及超过大小上限的
文件或嵌套的 Git 仓库。Git 会拒绝 merge，本地文件保持原样，同步也不会推送。根据 Git 诊断信息中的
路径，逐一处理后再运行 `dotbrain sync`：

- 自己在 `~/dotbrain` 里提交它，或者调高上限，让同步可以合并它。
- 把本地副本移出主目录。
- 用 `git restore <path>` 丢弃本地副本；如果它未被跟踪，直接删除。

### 同步被拒绝 {#home-sync-is-blocked}

doctor 报告 `home sync blocked: <state> in the dotbrain home`，`dotbrain sync` 也会失败。

主目录有 merge、rebase、cherry-pick 或 revert 正在进行，有未合并的路径，或处于 detached HEAD 时，
同步拒绝记录。这时记录会把冲突标记提交进去，或者提交到不属于任何分支的位置。在 `~/dotbrain` 里用 Git
完成或中止那个操作，切回分支，再运行 `dotbrain sync`。在此之前，hook 什么都不会记录。
你自己发起的 merge 会留在原处，同步不会替你中止它。

### 有提交等待推送 {#commits-are-waiting-to-be-pushed}

doctor 报告 `home sync: <n> local commits waiting to be pushed to <upstream>`。

上一次推送没有到达远程仓库。可能是机器离线了，也可能是远程有了新提交：完整同步最多推送四次（第一次
加三次重试）后放弃；Agent 每轮结束后的推送不会 fetch，被拒后就把提交留给下一次完整同步。这些提交是安全的。
下一次同步会推送它们，也可以现在运行 `dotbrain sync`。如果一直失败，在 `~/dotbrain` 里手动试一下
`git push`。

`home sync: no remote configured; sync commits stay local` 表示主目录的分支没有上游。添加一个私有
远程仓库并设为上游，做法见[快速开始](getting-started.md#_4-back-up-and-sync-your-dotbrain-home)。

### 关闭主目录同步 {#turn-home-sync-off}

在 `~/dotbrain/config.yaml` 的 `sync:` 下设置 `enabled: false`：

```yaml
# ~/dotbrain/config.yaml
sync:
  enabled: false
```

之后 hook 和 `dotbrain sync` 都不做任何事，doctor 报告 `home sync disabled`。主目录要你自己提交和推送。
`config.yaml` 通过远程仓库共享：你推送这个改动后，其他机器在下一次同步拉到它时也会关闭同步。同步提交
就是普通提交，不需要撤销什么。

## 常见问答 {#faq}

### Brain 里的内容会进入代码仓库吗？ {#does-anything-from-my-brain-reach-the-code-repo}

Brain 始终是私有的。仓库里只有被 gitignore 的链接和生成的 Codex Agent 定义，每一个都单独被忽略。
Brain 和 Beads 状态都放在 `~/dotbrain` 下，它是一个独立的 Git 仓库。

### 怎么在第二台机器上用 dotbrain？ {#how-do-i-use-dotbrain-on-a-second-machine}

先克隆你的 dotbrain 主目录，再安装插件和 CLI，然后逐个连接仓库：

```bash
git clone <your-remote> ~/dotbrain
dotbrain bootstrap
dotbrain wire --repo ~/repos/my-app
```

之后，[主目录同步](session-context.md#home-sync)会让两台机器上的 Brain 保持最新。
如果需要在多台机器之间实时共享任务跟踪，请用 [server 模式的 Beads 后端](beads-backend.md#server-mode)。

### Brain 能不放在 `~/dotbrain` 吗？ {#can-i-keep-the-brain-somewhere-other-than-dotbrain}

可以。把 `DOTBRAIN_HOME` 设为你想要的目录即可。

### 没有代码仓库能用 dotbrain 吗？ {#can-i-use-dotbrain-without-a-code-repo}

现在不行了。每个项目都需要一个仓库作为工作目录，不过它可以是只放文档的私有仓库。要把以前的 Brain-only 项目
迁过去，在那个仓库里运行 `dotbrain wire --project <project>`。

### 怎么让某个仓库不再使用 dotbrain？ {#how-do-i-stop-using-dotbrain-on-a-repo}

```bash
dotbrain unwire             # disconnect, keep the Brainspace
```

保留下来的 Brainspace 请用你自己的文件系统操作来归档或删除。见[项目连接](wiring.md#unwire)。

### 支持哪些 Agent？ {#which-agents-are-supported}

Claude Code 和 Codex，以及 [Hermes](getting-started.md#hermes)、[OpenCode](getting-started.md#opencode)、[Pi](getting-started.md#pi) 和 [Cursor](getting-started.md#cursor)。用 [`project.yaml`](configuration.md#project-yaml) 里的 `agents:` 选择项目使用哪些工作区。
