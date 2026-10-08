# 为什么用 Dotbrain？

不用 dotbrain，你也能给 Coding Agent 提供有用的项目上下文。问题在于：让这些上下文保持连通、保持最新、
保持私有，这件事是否已经麻烦到值得用一个工具来做。

## 我的 Coding Agent 本来就有的，它还能多给我什么？

Dotbrain 给项目知识和执行状态一个统一的存放位置，并提供把它连到 Claude Code 和 Codex 的命令。
Brain 里存放术语、决策、工作规则和设计；选定的技能和子 Agent 会放进 Agent 的工作区。

比如你记下了项目为什么选某个数据库，之后的会话可以直接读这条决策，不用再让你重新解释一遍。
插件提供查找和使用这些材料的约定，但决策还是得你自己记下来。Dotbrain 不会替代你的 Agent，
也不保证代码会更好。详见[架构](architecture.md)。

## 单独建一个私有 Git 仓库不就行了？

可以。这已经能给你私有、有版本记录的文档，也许就够用了。

Dotbrain 多做的是和代码 checkout 的连接：选择项目、链接到正确的 Brainspace、分发技能和子 Agent、
在多个 worktree 之间共享上下文，以及检查和修复这套配置的命令。这些约定你也可以自己写脚本实现。
如果你更愿意花时间维护项目知识，而不是维护这些连接，Dotbrain 就有用。

## 在代码仓库里 gitignore 私有上下文不行吗？

被忽略的本地上下文也可以用得很好。只是 Git 不会给它做版本管理，备份得另外安排。
[Claude Code](https://code.claude.com/docs/en/worktrees#copy-gitignored-files-into-worktrees)
和 [Codex](https://developers.openai.com/codex/app/worktrees/#copy-ignored-local-files-into-managed-worktrees)
都支持 `.worktreeinclude`，可以把选定的被忽略文件复制到它们管理的本地 worktree 里。如果你只需要
把这些文件带到新的 worktree，原生机制可能就够了。

Dotbrain 把长期保留的内容放在一个单独的私有目录里，每个 checkout 都连到同一个来源。所以对共享
上下文的修改，在所有已连接的 worktree 里都能看到，不需要同步副本。断开一个 checkout 时，Brainspace
会保留下来。本地链接和分发的资源仍然靠 gitignore 防止被误提交；区别在于它们的来源放在哪里、
怎么重新连接。这是存储和工作流程上的边界，不是访问控制：在已连接 checkout 里工作的 Agent
可以读取链接过来的内容。详见[项目连接](wiring.md)。

## 用 AGENTS.md 加几个技能不行吗？

对于公开的项目说明和少量稳定的偏好，这是个很好的起点。Dotbrain 不会动项目自己的运行时文件，
可以和这套配置并存。

当上下文多到一个简短的说明文件装不下时，它才值得：需要保留理由的决策、跨多个会话的设计、
私有的操作手册，以及需要在多个 checkout 之间保持一致的资源选择。它自带的技能会引导这套流程，
但并不是每个小改动都需要一份设计和一个 epic。详见[工作流程](workflow.md)。

## Dotbrain 真的能让 Agent 记住我的项目吗？

它保存的是新会话可以检索的书面上下文。它不会保存模型的内部记忆，也不会把整个项目历史塞进每次对话。

会话开始时的 hook 只注入 dotbrain 的共享约定。这份约定会引导 Agent 去读项目规则，并按需检索相关知识。
hook 能否生效取决于运行时，Agent 也仍然可能漏看或误解某份文档。有用的上下文需要写下来、
能被找到，并且持续维护。详见[会话上下文](session-context.md)。

## 用多个 Agent 或 worktree 时有什么不同？

Claude Code 和 Codex 可以访问同一个项目 Brain 和执行存储。链接出来的 Git worktree 会连到主
checkout 的 Brainspace，而不是拿到一份单独的上下文副本。选定的资源会按每个运行时需要的格式分发。

比如两个 worktree 在不同分支上工作时，可以查阅同一条决策记录。它们也共享执行状态，所以认领和
依赖关系可以帮助协调工作。更进一步的多 Agent 协作，请看
[Beads 的多 Agent 指南](https://beads.gascity.com/multi-agent)。
不过这并不能防止代码冲突，也不能防止同时编辑共享文档；Agent 之间仍然需要明确分工。跨机器使用时，
还需要自己安排私有 Git 和任务跟踪的同步。

## 我要额外承担哪些维护工作？

主要的持续工作是让项目知识保持有用：记录决策，项目变化时更新规则，删掉过时的指引。不管用什么方式
存放上下文，这些工作都免不了。Dotbrain 负责维护 CLI、插件、共享约定和资源分发。你要做的配置工作是
选择技能和子 Agent，在选择变化时运行 `dotbrain refresh`，并用 `dotbrain doctor` 检查连接。

任务跟踪的维护取决于你的选择。Beads 默认是 **embedded 本地模式**：不需要维护单独的服务器，
同一台机器上的 Agent 可以共用存储，但同一时间只能有一个写入者。**server 模式**通过本地或远程的
Dolt SQL 服务器支持多个客户端同时访问，代价是你要多运维一个服务器。跨机器使用时，需要配置共享的
远程服务器或 Dolt remote 同步。如果你在别处管理任务，也可以不用任务跟踪。详见
[Beads 后端](beads-backend.md)和
[Beads 的运行模式](https://beads.gascity.com/architecture/dolt#modes-of-operation)。

备份由你决定。私有的 Git 远程仓库可以备份 Brain 文档；如果还想备份任务数据，需要另外安排。
推送文档并不会备份 Beads 数据库。

## 什么时候不需要 dotbrain？

如果一个简短的 `AGENTS.md` 加上 Agent 原生的技能已经够用，或者工作周期很短，又或者你的私有仓库和
链接脚本维护起来很轻松，那就不用。无论用不用 dotbrain，每个贡献者都需要的公开项目指引都应该留在代码仓库里。

如果你总在反复解释同样的决策、在会话之间丢失上下文，或者要在多个 Agent 和 worktree 之间反复修复
私有上下文和资源，可以考虑 dotbrain。先从一个项目开始，看看省下的工夫是否抵得上配置成本。
[快速开始](getting-started.md)介绍了需要做些什么。
