# 升级到五个核心 skills

这个 breaking release 提供 `wire-brain`、`brain-convention`、`maintain-brain`、`work-graph` 和 `repo-rules`。
旧工程工作流程序和打包工作流 agents 已移除；仍需要旧工作流的用户请留在前一版本。
现有私有上下文、笔记、Beads 记录，以及用户的 skills 和自定义 agents 来源仍归你所有。

## 安全迁移 {#safe-transition}

修改实际安装前，先完成或安全交接正在写入的工作。记录实际 candidates、认领、待办、证据和剩余限制。
升级不会验收结果、关闭任务或重置额度。Brain/home 文件通过私有 Git 历史和备份保留；
Beads 通过 Dolt remote 或服务器备份单独保存，home sync 不备份 tracker。
同时保存回滚所需的配置和交付资源。更新匹配版本的 CLI 与插件，在新会话中检查
`dotbrain doctor` 和 `dotbrain refresh` 的结果。

## 旧声明与资源 {#old-declarations-and-resources}

项目声明 `packaged-subagents`、`retro`、`execution-engine`、`public-tracker` 和 `public-tracker-id`
已废弃。refresh 会报告并保留原声明；请明确检查和删除，保留无关设置。
`subagents` 只选择自己的来源；无前缀的 `reviewer` 等名称现在指向你的自定义文件。

只有完整内容匹配已知生成定义时，refresh 才移除旧打包 agents。修改过的文件、未知 `dotbrain-*` 文件
和归属不明的链接保留并报告。在会话可能发现它们之前，请明确检查并删除或迁移需要处理的资源。
现有 `RETRO.md` 笔记不动；核心不再要求检索、整理或写入复盘。

修改过的共享约定在被打包约定替换前，先复制到 Brain 的 `.dotbrain-preserved/`；wire 和 refresh 会报告位置。
修改过的旧 runtime bundles 移到 adapter 发现目录之外的 `.dotbrain-preserved/`。
这些副本仍是私有数据。归属不明的旧 skill caches 保留并报告，能确认归属的过时交付链接会清理。

## 选择工作流 {#workflow-selection}

核心不需要 pstack。可选的 `dotbrain-pstack` mode 需要单独准备干净的外部来源 checkout，
并通过项目 `pstack.enabled` / `pstack.source` 明确启用。它由 CLI 交付，不是 marketplace 的第六个核心 skill。
详见[设置与验证范围](workflow.md#pstack)。首批 native 验证目标是 Windows 本地 Claude Code 和 Codex；
来源身份和生成资源只是结构证据，不代表 native 通过。实际结果以精确 release 或 PR 的验证记录为准。

mode 链接和 `.dotbrain-pstack.json` 是被 gitignore 的生成资源。改变项目选择后，在各 checkout refresh，
检查保留资源的提示，再开启新会话。修改过的缓存、发现记录或其他工具的资源不会被静默覆盖或删除。
外部依赖保持固定，除非另行审阅并验证升级。

## 回滚 {#rollback}

恢复先前 release 及保存的配置和资源。还原旧私有文件或后端状态前，先协调升级后产生的新工作。
软件回滚不能覆盖更新的工作记录。
