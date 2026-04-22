# QA — GAS Extension E2E 测试

以 QA 测试工程师身份，通过 Playwright Electron 模式操作真实 VS Code Insiders，验证 GAS 扩展的 UI 行为和功能正确性。

## 前置准备

读取 QA 测试工程师 Skill（SKILL.md），按照 Skill 中定义的流程执行。

## 用户指令

{{input}}

## 快速参考

- `/qa run <name>` — 执行已保存的场景
- `/qa create "<描述>"` — 生成并保存新场景
- `/qa list` — 列出所有已有场景
- `/qa explore "<描述>"` — 即兴探索测试（不保存）
- `/qa loop [scope] [--max-rounds N] [--skip-fix]` — 测试→修复→回归循环
- `/qa watch [--interval N] [--scenario <name>]` — 长驻监测，新 commit 触发回归

场景文件位于 `scenarios/`。
截图输出到 `packages/vscode-adapter/dist/screenshots/`。
