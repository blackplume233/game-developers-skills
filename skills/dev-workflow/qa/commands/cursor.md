# QA — 通用真实操作验证

以 QA Engineer 身份操作真实产品入口，验证用户可见行为、关键流程、错误处理和回归风险。优先使用项目已有测试工具；没有现成工具时，用最小可行真实操作完成验证并沉淀测试用例。

## 前置准备

读取 QA Skill（SKILL.md），先发现项目的启动、构建、测试和用例存储约定，再按 Skill 中定义的流程执行。

## 用户指令

{{input}}

## 快速参考

- `/qa run <name>` — 执行已保存的场景
- `/qa create "<描述>"` — 生成并保存新场景
- `/qa list` — 列出已有场景
- `/qa explore "<描述>"` — 即兴探索测试，结束时总结是否保存用例
- `/qa loop [scope] [--max-rounds N] [--skip-fix]` — 测试→修复→回归循环
- `/qa watch [--interval N] [--scenario <name>]` — 长驻监测，新 commit 触发回归

默认场景文件位于项目内 `.qa/scenarios/`。
默认报告和截图输出到项目内 `.qa/reports/` 与 `.qa/artifacts/`。
