# Ship — GAS 扩展一站式交付

审查代码质量、构建、E2E 验证、提交、推送、(可选)打包 VSIX。

## 前置准备

读取 Ship Skill（SKILL.md），按照 Skill 中定义的五阶段流程执行。

## 用户指令

{{input}}

## 快速参考

- `/ship` — 默认流程：审查 → commit → push
- `/ship --vsix` — 额外打包 VSIX
- `/ship --skip-e2e` — 跳过 Playwright E2E
- `/ship --skip-push` — 仅 commit 不 push
- `/ship --message "feat: add chat history"` — 自定义 commit message
- `/finish-work` — 仅审查清单，不提交
- `/create-pr` — 提交后创建 GitHub PR
