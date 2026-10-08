# 故障排查与常见问题

排查任何问题都先运行只读的健康检查。它会报告机器是否就绪、项目连接情况和 Beads 状态的偏差，不会改动任何东西：

```bash
dotbrain doctor
```

## 常见问题 {#common-problems}

### Agent 不了解项目 {#the-agent-does-not-know-the-project}

会话开始时没有加载 dotbrain 约定。

1. 确认仓库已连接：仓库根目录应该有 `.brain`，并且指向一个目录。
2. 确认 Agent 的 shell 能在 `PATH` 上找到 CLI：`dotbrain --version`。找不到 `dotbrain` 时，hook 不会有任何输出。
3. **Codex：** 在 `/hooks` 里信任 dotbrain 的 hook，然后新开一个 thread。
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

### `dotbrain site` 失败 {#dotbrain-site-fails}

检查 `node --version`；站点需要 Node.js 22.12 或更高版本。顺着构建错误找到提到的文件和行：缺失的链接、
无效的 frontmatter、格式错误的 HTML 或 Vue 标记都可能导致构建失败。遇到 "Element is missing end tag" 时，
找一找没加反引号的占位符，比如 `<name>` 或 `<path>`，用行内代码包起来，表格里也一样。见
[Brain 站点配置](brain-site-configuration.md#what-fails-the-build)。

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

如果需要在多台机器之间实时共享任务跟踪，请用 [server 模式的 Beads 后端](beads-backend.md#server-mode)。

### Brain 能不放在 `~/dotbrain` 吗？ {#can-i-keep-the-brain-somewhere-other-than-dotbrain}

可以。把 `DOTBRAIN_HOME` 设为你想要的目录即可。

### 没有代码仓库能用 dotbrain 吗？ {#can-i-use-dotbrain-without-a-code-repo}

可以。`dotbrain wire --no-repo --project <project>` 会创建一个只有 Brain 的 Brainspace。

### 怎么让某个仓库不再使用 dotbrain？ {#how-do-i-stop-using-dotbrain-on-a-repo}

```bash
dotbrain unwire             # disconnect, keep the Brainspace
```

保留下来的 Brainspace 请用你自己的文件系统操作来归档或删除。见[项目连接](wiring.md#unwire)。

### 支持哪些 Agent？ {#which-agents-are-supported}

Claude Code 和 Codex。用 [`project.yaml`](configuration.md#project-yaml) 里的 `agents:` 选择项目使用哪些工作区。
