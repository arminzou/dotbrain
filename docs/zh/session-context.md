# 会话上下文

在已连接的仓库里，Agent 会话一开始，dotbrain 约定就已经在上下文里了。本页解释注入了什么、怎么注入的，
Agent 会自己去读哪些内容，以及会话的 hook 怎样同步 dotbrain 主目录。

## 会话开始时发生了什么 {#what-happens-at-session-start}

启动时，runtime hook 在已连接的 checkout 中提供共享约定。
所选工作流按需读取相关项目记录。

插件的 `SessionStart` hook 运行 `dotbrain hook session-start`。这个 hook 在启动、恢复会话、
`/clear` 和上下文压缩时都会触发，所以约定在上下文重置后依然存在。注入约定之前，它会先运行
[主目录同步](#home-sync)。

## 注入了什么 {#what-is-injected}

共享约定 `.brain/DOTBRAIN.md` 由 Dotbrain 维护，通过 `dotbrain refresh` 保持最新。
选择 pstack 的项目另附有大小限制的 mode 位置和依赖记录指针；工作流正文与私有知识不注入。
它涵盖连接规则、执行状态放在哪里、公开/私有的边界，以及 Brain 的目录结构。

项目自己的文件不会被注入：

| 文件 | 加载方式 |
| --- | --- |
| `.brain/DOTBRAIN.md` | 由 hook 注入 |
| 公开的 `AGENTS.md` 和根目录 `RULES.md` | 仓库入口指引修改或审阅代码的 Agent 读取 Git 跟踪的规则，没有 Brain 也能用 |
| `.brain/CONTEXT.md`、`adr/`、`designs/` | 工作需要时由 Agent 读取 |
| `.brain/docs/` | Agent 在回答项目如何运作之前先搜索这里 |
| Beads 工作流入门 | dotbrain 不注入；Agent 需要时运行 `bd prime` |

如果也想注入 Beads 的入门说明，可以用 `bd setup claude` 或 `bd setup codex` 添加 Beads 自己的 hook。
dotbrain 不会安装它。

::: info 为什么不全部注入？
dotbrain 用 10,000 字节的预算测试会话启动时注入的内容。这个预算来自对 Claude Code 实际行为的测量：
9,961 字节到达了模型，而 10,010 字节则被写到了一个文件里。它不是在所有 runtime 上都验证过的上限。
`DOTBRAIN.md` 的大小是有上限的，而仓库规则和私有知识会随项目增长。只注入约定，就能让内容保持在预算以内。
:::

## 主目录同步 {#home-sync}

插件注册了三个 hook。每个都会同步 dotbrain 主目录，也就是存放所有 Brainspace 的那个 Git 仓库。这样
Brain 的改动不用手动提交和推送，就能到达你的其他机器。

| Hook | 运行 | 做什么 |
| --- | --- | --- |
| `SessionStart` | `dotbrain hook session-start` | 运行一次完整同步，最多等 10 秒，然后注入约定。超时的同步会在后台继续跑完，会话从本地状态开始。上下文压缩时只记录和推送，因为压缩发生在一轮对话中间。 |
| `Stop` | `dotbrain hook stop` | 主 Agent 每轮结束后，在后台启动一次只记录和推送、不 fetch 的同步，然后立即返回。文件不会在 Agent 运行期间被改动。 |
| `SessionEnd` | `dotbrain hook session-end` | 在后台启动一次完整同步，然后立即返回；`/clear` 时跳过，由随后的 `SessionStart` 同步。 |

其他 runtime 的 hook 改为调用 `dotbrain hook run`，它不读取 hook 的输入数据。用
`--event startup|resume|clear|compaction|turn-end|session-end` 指定事件，用 `--checkout PATH`
指定 checkout（默认是当前工作目录），加 `--format json` 则把约定输出为
`{"additional_context": "..."}`。各事件的同步方式与上表对应的 hook 相同：会话开始类事件
（`startup`、`resume`、`clear`）等待完整同步并注入约定；`compaction` 和 `turn-end` 只记录和推送；
`session-end` 启动一次完整同步。清空会话时只发送 `clear`，不发送 `session-end`。

一次完整同步分四步：

1. **记录。** 所有没提交的改动都变成同步提交：每个有改动的 Brainspace 一个，其余改动合成一个
   `home` 提交。超过大小上限的文件和嵌套的 Git 仓库会被跳过并报告。你自己写的提交保持不变。
2. **Fetch** 主目录当前分支的上游。
3. **整合。** 把上游 merge 到当前分支。两台机器都改了同一个文件时，
   这台机器的版本留在原处，另一台机器的版本存到旁边，成为冲突副本。一边删了文件、另一边改了它时，
   保留改动。如果传入的改动会覆盖未提交或被忽略的本地文件，Git 会拒绝 merge，同步会报告 Git 的
   原始诊断信息，不再推送。
4. **推送。** 如果远程仓库在此期间有了新提交，同步会重新 fetch 再试，最多三次。从不强制推送。

主目录同步不出声，并且失败时放行。它不往 Agent 的上下文里写任何内容，失败也不会阻塞会话。离线的机器和
没有远程仓库的主目录，会把同步提交留在本地，等之后的同步再推送。hook 只在连接了 Brainspace 的
checkout 里，或在 dotbrain 主目录本身里同步。同一台机器上有锁，两次同步不会同时运行。会话开始时的
完整同步会在 10 秒的总等待时间内短暂等待锁释放；上下文压缩后的只记录和推送同步，以及其他入口，
遇到锁被占用时会立即返回。想手动同步就运行
`dotbrain sync`；想查看待推送的提交、冲突副本和被跳过的文件，就运行 `dotbrain doctor`。关闭同步见
[`sync:`](configuration.md#sync)。

主目录同步不会同步 Beads 任务跟踪，它走 `dotbrain beads sync` 自己的路径。

::: warning 已知限制
- 同步在记录前会先取消所有暂存，所以只存在于暂存区的状态（部分暂存的代码块、`git rm --cached`、
  暂存的权限变更）会被工作区内容替换。
- 主目录里嵌套的 Git 仓库永远不会被记录。
- hook 正在提交时，你在主目录里运行的 Git 命令可能碰到 Git 的锁错误。重新运行即可。
- 两台机器改了同样的行时，解决冲突的合并会改写共享主目录里的这些文件。在这一步进行期间，
  同一台机器上的其他会话可能短暂看到或覆盖它们。如果合并会覆盖尚未提交的改动，同步会拒绝合并。
:::

## 失败时放行 {#failing-open}

hook 从不阻塞会话。在 git 仓库之外、在没有连接的仓库里，或者 `PATH` 上没有 `dotbrain` 时，它什么都不输出，
正常退出。这样做的代价是，配置坏了也不会有提示：如果已连接仓库里的会话不知道约定，请运行
`dotbrain doctor`。见[故障排查](troubleshooting.md#the-agent-does-not-know-the-project)。

## 各 runtime 的说明 {#runtime-notes}

- **Claude Code** 装好插件后就会运行这些 hook。
- **Codex** 只在你信任插件 hook 之后才运行它们：在 `codex` 里打开 `/hooks`，信任 dotbrain 的几个
  hook，然后新开一个 thread。在此之前，Codex 会话既不会注入约定，也不会同步。Codex 给会话结束的
  hook 留的时间很短，所以这个 hook 只负责启动同步，然后立即返回。Codex 是否只在主 thread 上触发
  `Stop`，以及是否在后台运行 `Stop` hook，目前还没验证。Stop 和会话结束时的同步发现已有同步在运行，
  都会立即退出；只推送的同步也很快返回。
- **Hermes**（见 [Hermes](getting-started.md#hermes)）在插件启用后就会运行
  这些 hook。每个会话第一次请求模型之前，插件会运行 `dotbrain hook run --event startup`，把约定附在第一条
  用户消息里，而不是放进 system prompt。Hermes 会把它留在会话历史里，所以恢复的会话会为同步运行 `resume`，
  但不会再加一份。压缩把它从历史里去掉之后，下一轮会运行 `compaction`，再把它加回来。Hermes 默认会把超过
  10,000 个字符的 hook 内容转存到文件里，所以约定必须比这个小。Hermes 每轮结束都会触发它自己的会话结束
  hook，所以这个 hook 只在后台启动 `turn-end` 推送；真正退出时才运行 `session-end`。委派出去的 subagents
  不注入约定，也不同步。
- **OpenCode**（见 [OpenCode](getting-started.md#opencode)）在 plugin 文件放进
  它的配置目录后就会运行这些 hook。每个会话第一次请求模型之前，plugin 会运行 `dotbrain hook run --event startup`，
  并把约定加进这个会话每次请求的 system prompt。不是当前 OpenCode 进程创建的会话（比如用 `opencode run -c`
  继续的会话）会改为运行 `resume`。压缩之后运行 `compaction`，约定照样会加上。一次运行结束、会话进入空闲时，
  plugin 在后台启动 `turn-end` 推送。OpenCode 退出时，为每个空闲会话启动 `session-end`。强制结束 OpenCode 或者
  直接关掉窗口会跳过这一步，下次会话启动时的同步会补上。重新加载配置也会关闭 plugin，但对还在运行的会话只推送。
  task subagents 不注入约定，也不同步。
- **Pi**（见 [Pi](getting-started.md#pi)）在扩展放进它的 Agent 目录后就会运行
  这些 hook。每次会话启动时，扩展运行 `dotbrain hook run`（`startup`、`resume`，`/new` 对应 `clear`，重新加载或
  fork 对应 `compaction`），并在这个会话的每次运行里把约定作为 system prompt 的一节加上。压缩之后运行
  `compaction`，约定照样会加上；刷新失败时保留原来的约定。一次运行结束时，在后台启动 `turn-end` 推送。`/quit`
  运行 `session-end`。直接关掉控制台窗口很可能会跳过这一步，下次会话启动时的同步会补上。
- **Cursor**（见 [Cursor](getting-started.md#cursor)）运行 dotbrain 加进 `~/.cursor/hooks.json` 的 hook。在 `sessionStart`
  时，它以 Cursor 的项目目录作为 checkout 运行 `dotbrain hook run --event startup`，并把约定作为上下文返回；这个上下文会随
  会话的每次请求发送，所以压缩不会丢掉它。恢复的会话保留开始时的约定；Cursor 不会为它运行 `sessionStart`，所以也没有启动同步。
  每次 `stop` 在后台启动 `turn-end` 推送，`sessionEnd` 运行 `session-end`。直接关掉控制台窗口很可能会跳过这一步，
  下次会话启动时的同步会补上。
- 在不支持 hook 的 runtime 里，调用 `brain-convention` skill 手动加载约定，并自己运行 `dotbrain sync`。

## 自定义 subagents {#subagents}

Dotbrain 交付选中的自定义 Claude Code 和 Codex 定义，不附带工作流 agents。
通过全局 `config.yaml` 或项目 `project.yaml` 中的 `subagents:` 选择。
`dotbrain-` 前缀保留，以保护需检查的旧版资源。Hermes、OpenCode、Pi 和 Cursor 不接收 Dotbrain 原生自定义 subagents。

Claude 定义使用符号链接；Codex 定义使用带 `# dotbrain-managed-agent: v1` 标记的生成 TOML 文件。
请修改私有来源，而不是生成副本。`dotbrain subagents link` 同步当前 checkout，`--scope global` 同步全局主目录。
其他工具的资源与冲突会保留并报告。doctor 检查交付状态，runtime 实际消费定义需要成功的原生调用另行证明。

任务分派、上下文读取与记录的时机、验证及恢复由所选工作流决定。
可选的 [pstack mode](workflow.md#pstack) 单独交付到启用它的 Claude Code 和 Codex 项目，不是打包 subagent。
启动上下文可列出交付位置和被 gitignore 的 `.dotbrain-pstack.json` 依赖记录；改变选择后请重启会话。
