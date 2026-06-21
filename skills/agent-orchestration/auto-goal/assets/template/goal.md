# Auto Goal 任务

## 目标

<!-- 保持简洁。把用户请求改写成详细、无歧义的基础目标。包含紧凑的完成证据。保留用户意图；没有用户确认时不要缩小目标。 -->

- 基础目标:
- 完成证据:

## 约束

<!-- 保持简洁。包含范围限制、排除项、语言偏好、技术要求、验证命令、产物目录、依赖策略、安全边界和外部阻塞。 -->

- 文档语言:
- 回复语言:
- 技术要求:
- 验证命令:
- 产物目录约定:
- 依赖策略:
- 安全边界:

## 执行指导

<!-- 每轮如何从基础目标推导子目标、执行、验证并更新任务文件。保持简洁。 -->

- 每轮开始前重新读取本文件。
- 遵循仓库语言偏好、技术要求、验证命令和产物目录约定。
- 所有持久目标文档和最终报告默认使用 `artifact_language` 指定语言。
- 每轮只推导一个有边界的子目标。
- 循环细节记录到 `loops/loop-XXX.md`。
- 错误路径、失败计划和有用模式记录到 `references.md`。
- 如果子目标太宽，创建 `child-goals/` 下的子 Auto Goal 任务。
- 验证子目标后再更新根状态。

## 状态

```yaml
status: draft
updated_at: YYYY-MM-DD
artifact_language: zh-CN
execution_mode: simulated-file-goal
native_goal_id: null
current_loop: null
next_sub_goal: null
last_verified_loop: null
references: references.md
```
