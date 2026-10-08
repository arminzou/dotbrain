# 学习你的项目

Dotbrain 能帮你跨多个会话学习自己在做的项目。`teach-me` 技能会根据项目的 Brain 和当前代码来讲解，
检查你的理解，并保存足够的私有学习状态，让下一个会话能从你上次停下的地方接着来。

先在装好 dotbrain 插件的[已连接项目](getting-started.md)里，对 Agent 说：

> Teach me how this project handles failed deliveries. I want to be able to diagnose one myself.

Agent 会先确认主题和你的目标，然后在对话中讲解。实现过程中的一个小问题，简单回答就行，
不需要学习路径，也不需要保存成课程。

## 进度和理解是两回事 {#progress-and-understanding-are-different}

学习路径描述的是通往目标的步骤，学习记录保存的是你已经理解了什么的证据。把两者分开，之后的会话
既能找回你学到了哪一步，也能判断该讲到什么深度。

| 产物 | 内容 | 下一个会话用它来 |
| --- | --- | --- |
| 学习路径 bead | Description 里是一节课大小的步骤；Notes 里是进度和下一步 | 找到从哪里继续 |
| 学习记录 | 你展示出的理解、你说过的已有知识，或被纠正的误解 | 决定接下来讲什么、考什么 |
| 学习待办 bead | 每个留到以后再学的概念一条评论 | 提出可以并入路径的问题 |
| 保存的课程和参考 | 经你认可的讲解和配套的速查页 | 之后阅读或练习 |

光是讨论过，并不代表已经理解。Agent 会让你解释一个概念或做一个练习，给你反馈，在有值得保留的证据时
写一条学习记录。它会先写记录，再把学习路径的这一步标记为完成。

## 按学习路径学 {#walk-a-learning-path}

目标比较大时，可以让它规划一条路径：

> Help me learn the retry mechanism over a few sessions. Start with one practical exercise.

Agent 会和你商定主题、目标和路径。跨会话的路径会成为一个 `learn: <topic> path` 学习路径 bead；
一次会话就能学完的短路径，可以只留在对话里。

学习工作区属于项目。课程按主题组织，主题在 Brain 里的 `learning/MISSION.md` 中命名。mission 写明你
为什么要学、想学会做什么。教学偏好和可信来源能让之后的会话一直有用。

在新会话里继续时，可以说：

> Continue my learning path on retries. Read my progress and learning records, then resume the
> next step.

Agent 会读取学习路径 bead 和这个主题的学习记录，查看暂存的概念，然后从下一个该学的步骤继续。
它可能会先问一个回忆题来检验你还记不记得，而不是重新从头讲，或者假定之前讲过的你都还懂。

## 工作中先把问题存起来 {#park-a-question-while-working}

实现过程中，你可以先把问题存下来，不用切换到教学会话：

> Park this for learning: why does retrying this operation require an idempotency key?

Agent 会找到或创建一个 `learn: <topic> backlog` 学习待办 bead，为这个概念加一条评论。评论记录问题、
目前的答案，以及它是在哪里冒出来的。每个概念单独一条评论，问题多了也容易区分。

恢复学习时，Agent 会读这些评论，帮你把概念变成一节课大小的步骤。“并入第 2 步”“已讲”“放弃”这类结果
会作为新评论记下，并引用原来的评论。更正时也会保留之前的评论。旧版本技能存在 Notes 里的概念同样会被读取。

## 学习和实现分开 {#keep-learning-separate-from-implementation}

每个项目有一个长期存在的 **Learning epic**。它的子项是各个主题的学习路径 bead 和学习待办 bead。
epic 和子项都带 `learning` 标签。

epic 用来把学习内容归在一起方便浏览。**每个子项也必须保持 deferred 状态**，这样它们才不会出现在
Beads 的 `bd ready` 实现队列里。把父项设为 deferred 并不会让子项也变成 deferred。执行技能还会额外
跳过带 learning 标签的条目，作为兜底。

可以用 Beads 查看这些状态：

```bash
bd list --label learning --json
bd comments <backlog-id> --json
bd defer <learning-child-id>
bd ready --json
```

Dotbrain 的技能通过 Beads 维护这些状态，并没有单独的 Dotbrain 学习 CLI。如果项目没有执行引擎，
路径就只留在对话里，概念也不会存成 bead。

## 有用时再保存成课程 {#capture-a-lesson-when-it-helps}

讲解不会自动生成课程。学到有用的东西之后，可以说：

> Capture what we learned as a lesson, with a short reference and a retrieval exercise.

Agent 会先提出标题、主题、章节、问题和来源，经你认可后再写。课程和参考放在 Brain 的 `learning/`
工作区里，和 mission、偏好、术语表、资源和学习记录在一起。依赖代码的讲解会链接到核对时所用提交的仓库代码。

这些内容都留在你的私有 Brain 里。[Brain 站点](brain-site.md)可以在本地渲染它们，并加一个 Learn 侧边栏，
但站点是可选的。没有站点时，课程的 Markdown 和配套链接写完就算完成。如果声明了学习站点，Agent 会按它的
发布指南操作并运行检查。提交或发布仍然需要你授权。

## 把学到的变成公开的项目文档 {#turn-learning-into-public-project-docs}

学习过程中可能会发现对其他用户或贡献者有用的项目知识：一个不清楚的安装步骤、一个恢复流程，
或者某个功能是怎么工作的。和 Agent 一起学一个主题时，可以想想这些知识是否应该放进项目的公开文档。

可以让 Agent 根据你学到的内容提议一份公开指南。要面向公开读者来写，论述以项目实际情况为依据，
只包含适合公开的上下文。要重新写一份文档，而不是复制私有课程或学习记录；私有的运维细节和敏感上下文
留在 Brain 里。

比如，一节诊断投递失败的课程，可能会引出一份公开的故障排查指南，包含受支持的检查和恢复步骤。
私有课程可以保留你的练习和项目特有的上下文，公开指南则帮助所有使用这个项目的人。

编写或发布公开文档和教学是两件事。起草前先商定读者和范围，提交或发布也要单独授权。

这套流程由内置的 [teach-me 技能](skills.md#learning)定义。
