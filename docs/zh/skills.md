# Skills

Dotbrain 插件内置五个独立于工程工作流的核心 skills。它们不依赖私有 skill 库。
全局自选 skills 在 `~/dotbrain/config.yaml` 配置，项目自选 skills 在
`brainspaces/<name>/.brain/project.yaml` 配置；这些选项不会改变插件的核心列表。

## 选择和同步 skills {#select-and-reconcile-skills}

Codex 项目 skills 链接到 `<checkout>/.agents/skills/`。配置和 subagents 仍放在 `.codex/` 下；全局 skills 继续
使用 `~/.codex/skills/` 和配置的 profile 主目录。Claude Code 和其他 runtime 的目标位置不变。

`wire`、`refresh` 和 `skills link` 会根据链接目标判断归属，迁移 `.codex/skills/` 下 dotbrain 自己的旧链接。
选中的旧链接会在新链接分发成功后移除，不再选中的自有链接会被清理。无法确认归属的文件、目录和链接都会保留并
报告；新位置发生冲突时，旧链接也会保留。处理冲突后重新运行即可。每个分发的资源都单独被 gitignore，
`unwire` 会清理新旧位置的自有链接。这些检查只能证明文件系统状态，runtime 是否发现和调用了 skills 需要另行验证。

两种范围都可以选单个 skill，也可以选一个 skill bundle 目录：

```yaml
# ~/dotbrain/brainspaces/my-app/.brain/project.yaml
skills:
  - my-collection/specific-skill
  - another-collection
```

```yaml
# ~/dotbrain/config.yaml
version: 4
profiles:
  claude-code: [~/.claude-work]
skills:
  - another-collection
```

全局链接使用各 runtime 的默认主目录。Claude Code 和 Codex 还可通过 `profiles` 添加额外主目录，skills 会
链接到每个主目录下的 `skills/`，不存在的主目录会跳过。请填写 runtime 主目录，不要填写项目 checkout
内的目录。详见[配置](configuration.md#global-skills)。

包含 `SKILL.md` 的目录只选中它自己，即使它下面还有子 skill。否则，dotbrain 会递归查找所有包含 `SKILL.md` 的
子目录，`node_modules` 除外。重复选中同一来源会去重。不同来源映射到同一个目标名（包括在不区分大小写的文件系统
上只有大小写不同）时，会在改动目标之前失败。路径不存在、不是目录或 skill bundle 为空时，也会失败并给出可操作的提示。

```bash
dotbrain skills list                         # discover sources
dotbrain skills link                         # current wired checkout
dotbrain skills link --project my-app         # registered checkout
dotbrain skills link --scope global           # explicit global homes
dotbrain skills link --runtime codex           # declared Codex workspace only
```

在选中的 skill bundle 里增删 skills，下次同步时就会生效，声明本身不变。被移除的、dotbrain 自己的链接会被清理，
其他来源的条目会保留。`projects show`、skills 目录和 doctor 都使用同样的展开结果。

在 `link` 后面写上 skill 或 bundle，就能一步完成选择和链接；用 `unlink` 取消选择并移除链接：

```bash
dotbrain skills link my-collection/specific-skill              # 当前 checkout 的项目
dotbrain skills link another-collection --scope global          # 所有项目
dotbrain skills unlink my-collection/specific-skill
```

这些命令只改动该范围的 `skills:` 列表，注释和文件其他部分保持原样。条目不存在、名称冲突，或者
dotbrain 无法精确编辑的写法，都会在文件改动前失败；这时请手动编辑列表。条目不能和 `--all` 一起用：
全局范围本来就覆盖所有项目。

## 来自外部仓库的 skills {#external-repositories}

你的 skill 库是 `~/dotbrain/skills`。外部 skill 仓库作为 dotbrain 主目录的 Git submodule 加进来，
[主目录同步](session-context.md#home-sync)按提交把它共享给你的其他机器：

```bash
dotbrain skills add https://github.com/backnotprop/pstack.git   # skills/pstack，已提交
dotbrain skills link pstack/skills/how                          # 选择你要的 skill
dotbrain skills update                                          # 所有仓库更新到最新提交
dotbrain skills update pstack --ref v0.15.36                    # tag、分支或提交，也可以更旧
dotbrain skills remove pstack                                   # 处处取消选择、移除、提交
```

- **`add`** 把仓库克隆到 `skills/<name>`（`--name` 改文件夹名，`--ref` 固定版本），没有任何 `SKILL.md`
  的仓库会被拒绝。它提交仓库，并为找到的每个 skill 列出对应的 `link` 命令。它不会选择任何 skill。
- **`update`** 把每个仓库移到远程的最新提交，或者把一个仓库移到 `--ref`，逐个提交，然后重新链接
  所有项目和全局目录，让选中 bundle 里新增的 skills 出现、被删的消失。
- **`remove`** 在 `config.yaml` 和每个 `project.yaml` 里取消选择这个仓库的 skills，移除 submodule
  和它克隆的数据，一起提交，然后重新链接。

仓库有未提交的改动或没推送的提交时，`update` 会跳过它，`remove` 会拒绝。先推送或丢弃这些改动。

主目录同步让各台机器保持一致：

- **其他机器。** 完整同步会 checkout 每个记录的提交，并克隆缺失的仓库。`dotbrain bootstrap` 也会
  克隆它们，所以新克隆的主目录在第一次会话前就有了这些 skills。
- **用 Git 做的改动。** 用 `git submodule add` 加的仓库，或者在仓库里 `git pull` 前移的提交，只要
  这个提交已经在仓库自己的远程里，下次同步就会记录。只存在于你机器上的提交，别的机器取不到。
  同步从不记录更旧的提交，因为还没跟上的机器看起来也是这样；要回退，用 `dotbrain skills update --ref`。
- **不动本地工作。** 仓库有未提交的改动或没推送的提交时，不会被记录，也不会被移动。同步会报告它，
  其余内容照常整合。

两台机器为同一个仓库记录了不同的提交时，同步会停下，不做 merge，并报告这个情况。在 `~/dotbrain`
里 merge，在 submodule 里 checkout 要保留的提交，`git add` 它，提交，然后再同步。`dotbrain doctor`
会报告没有克隆、有未提交改动，或者不在记录提交上的仓库。

## 核心能力 {#core-workflow}

| Skill | 能力 |
| --- | --- |
| `wire-brain` | 创建、连接、检查和修复 Brainspace 与 runtime 资源 |
| `brain-convention` | 解释共享的工作区身份、资源归属、记录含义和隐私约定 |
| `maintain-brain` | 记录和维护私有的术语、决策、设计、发现和参考资料 |
| `work-graph` | 查看和维护原生 Beads 工作记录、依赖和归属 |
| `repo-rules` | 按要求初始化和协调已采纳的仓库要求，评估执行机制 |

五个 skills 均允许模型按其职责调用。工程规划、执行、审阅和交付由所选工作流负责。
写作和语法参考位于 `maintain-brain/references/`。

## 操作约定 {#optional-skills-invoked-by-name}

会话启动 hook 提供共享约定。未运行 hook 时，可调用 `brain-convention`。
Claude Code 使用 `/dotbrain:<name>`；Codex 使用已安装 runtime 展示的 skill 名称。

## 自定义 subagents {#subagents}

插件不再提供工作流 agents。你选定的自定义 Claude 和 Codex agents 仍通过
`config.yaml` 和 `project.yaml` 的 `subagents:` 配置交付。Claude 定义使用链接，
Codex 定义使用生成的 TOML 文件；源文件保存在私有 home 中。
`dotbrain-` 前缀保留给旧版资源，防止覆盖需要检查的旧文件。

## 安装 {#installing-them}

Claude Code 和 Codex 通过 marketplace 插件加载核心 skills。Hermes、OpenCode、Pi
和 Cursor 使用各自的插件或资源交付路径；安装命令见[快速开始](getting-started.md)。

## 旧版资源与复盘笔记 {#retrospectives}

旧工作流入口、角色组合和强制复盘流程已移除。现有 `RETRO.md`、私有来源、工作记录
和历史保持可恢复。修改过或归属不明确的旧资源保留并报告。
更新前请阅读[升级说明](upgrading.md)，检查备份和当前工作状态。

## 可选工程 mode {#optional-engineering-mode}

CLI 只向明确启用的项目交付 `dotbrain-pstack`，它不是 marketplace 的第六个核心 skill。
详见[设置与验证范围](workflow.md#pstack)。
