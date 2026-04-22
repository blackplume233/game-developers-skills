---
name: ship
version: 1.0.0
description: 'GAS 扩展交付流水线。审查代码质量 → TypeCheck → 构建 → E2E 验证 → 提交 → 推送 → 打包 VSIX。触发方式：用户提及 "/ship"、"交付"、"提交推送"、"打包发布"、"ship it"、"发版" 等关键词时激活。'
---

# GAS Extension Ship

一站式交付：审查 → 构建 → 验证 → 提交 → 推送 → (可选)打包 VSIX。

## 命令格式

```
/ship [options]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--skip-e2e` | 跳过 Playwright E2E 验证 | 不设置 |
| `--skip-push` | 仅 commit，不 push | 不设置 |
| `--vsix` | 构建后打包 VSIX 安装包 | 不设置 |
| `--message "<msg>"` | 自定义 commit message | 自动生成 |

---

## 执行流程

### Phase 1: Review（审查清单）

在提交前执行全部质量检查。**任何 ❌ 项都阻断流程**。

#### 1.1 代码质量

```bash
cd packages/vscode-adapter

# TypeScript 类型检查（覆盖 core + vscode-adapter）
npx tsc --noEmit

# 构建（验证 esbuild 无报错）
pnpm build
```

```bash
cd packages/core

# Core 包类型检查
npx tsc --noEmit

# Core 单元测试
pnpm test
```

#### 1.2 模式扫描

对 `git diff --name-only` 变更的 `.ts` 文件（排除 `.test.ts`、`.d.ts`），检查：

| 模式 | 严重性 | 说明 |
|------|--------|------|
| `console.log` | ❌ | 使用 VS Code OutputChannel 替代 |
| `any` 类型 | ❌ | 必须有明确类型（`eslint-disable` 注释除外） |
| 非空断言 `!` | ⚠️ | 尽量用 optional chaining 或 guard |
| `TODO` / `FIXME` | ⚠️ | 确认是否应修复再提交 |
| 硬编码密钥/token | ❌ | 使用 SecretStorage |

#### 1.3 本地敏感信息过滤

在进入 commit 前，扫描 staged 文件内容，阻断以下信息进入仓库：

| 模式 | 严重性 | 说明 |
|------|--------|------|
| 用户主目录绝对路径 | ❌ | 如 `C:\\Users\\<name>`、`/Users/<name>`、`/home/<name>` |
| 工作区/临时目录绝对路径 | ❌ | 如项目本机绝对路径、`AppData`、`Temp`、`.codex`、`.ssh` |
| 本地凭据/认证产物 | ❌ | 如 `auth.json`、cookie、session、refresh token、access token |
| 私有 API Key / Secret | ❌ | 如 `sk-`、`ghp_`、`Bearer `、`OPENAI_API_KEY=` |
| 私有服务地址/账号 | ⚠️ | 仅本机可访问的 host、邮箱、用户名，需确认是否应脱敏 |

命中任一 ❌ → **停止 ship**，先脱敏、改成占位符、或改为通过 SecretStorage / 环境变量读取。

#### 1.4 ESM 格式验证

检查 `esbuild.mjs` 中 `format` 是否为 `'esm'`。如果是 `'cjs'` → **❌ 阻断**（扩展无法加载）。

#### 1.5 E2E 验证（除非 --skip-e2e）

```bash
cd packages/vscode-adapter
pnpm test:agent
```

启动 VS Code Insiders，执行 smoke test，截图验证。
如果 smoke test 失败 → **❌ 阻断**。

#### 1.6 输出审查报告

```
## 审查报告

| 检查项 | 结果 |
|--------|------|
| tsc --noEmit (vscode-adapter) | ✅ / ❌ |
| tsc --noEmit (core) | ✅ / ❌ |
| pnpm build | ✅ / ❌ |
| pnpm test (core) | ✅ / ❌ |
| console.log | ✅ 无 / ❌ N处 |
| any 类型 | ✅ 无 / ❌ N处 |
| 本地敏感信息 | ✅ 无 / ❌ N处 |
| ESM format | ✅ / ❌ |
| E2E smoke test | ✅ / ⚠️ 跳过 / ❌ 失败 |
| .omm/ 架构文档 | ✅ 已更新 / ⚠️ 无需更新 |
```

有 ❌ → 停止流程，输出修复建议。

---

### Phase 1.5: Architecture Docs（架构文档更新）

使用 oh-my-mermaid 保持 `.omm/` 架构文档与代码同步。

#### 判断是否需要更新

检查 `git diff --name-only` 变更文件，如果包含以下路径则**必须更新**：

| 变更路径 | 影响的 omm 视角 |
|----------|----------------|
| `packages/*/src/**/*.ts`（非 `.test.ts`） | `overall-architecture` |
| `packages/*/package.json` | `overall-architecture`（依赖关系可能变化） |
| 新增/删除 `packages/*/src/` 目录 | `overall-architecture` + `extension-points` |
| `packages/*/src/events/**` | `data-flow` |
| `packages/*/src/session/**` | `data-flow` |
| `packages/*/src/capabilities/**` | `extension-points` |
| `packages/*/src/runtime/**` | `extension-points` |

如果变更文件**仅涉及**测试、文档、配置文件（`.mdc`、`.md`、`.json` 非 package.json），**跳过**此步骤。

#### 更新方式

对受影响的视角，读取变更文件的新内容，更新对应节点的 `description.md` 和 `diagram.mmd`。

**规则**：
- 仅更新**受变更影响**的节点，不要重写未变化的节点
- 新增包/模块时，在对应视角创建新的子元素（创建目录 + description.md）
- 删除包/模块时，删除对应的 `.omm/` 子目录
- element ID 使用英文 kebab-case，描述内容使用中文
- 图表标签格式：`节点名称\n文件路径`
- 每条边必须有标签：`A -->|"关系说明"| B`

---

### Phase 2: Commit（提交）

#### 2.1 查看变更

```bash
git status
git diff --stat
git log --oneline -5
```

#### 2.2 生成 Commit Message

分析 `git diff --staged`（或 `git diff`），按 Conventional Commits 生成：

```
<type>[scope]: <description>
```

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 仅文档 |
| `refactor` | 重构（无功能变化） |
| `test` | 测试相关 |
| `build` | 构建/依赖 |
| `chore` | 杂项 |

#### 2.3 暂存并提交

```bash
git add -A
git commit -m "$(cat <<'EOF'
<type>[scope]: <description>

<optional body>
EOF
)"
```

**安全检查**：提交前扫描 staged 文件，**绝不提交**：
- `.env`、`*.key`、`credentials.json`
- 包含 `sk-`、`token`、`secret` 字面值的文件
- 包含本机绝对路径、用户目录、`.codex` / `.ssh` / `auth.json` / cookie / session 凭据的文件

---

### Phase 3: Push（推送）

除非 `--skip-push`：

```bash
git push origin <当前分支>
```

如果 push 失败（权限/冲突），输出诊断但不重试。

---

### Phase 4: Package（可选，--vsix 时执行）

```bash
cd packages/vscode-adapter
pnpm package:vsix
```

输出 VSIX 文件路径和大小。

---

### Phase 5: 最终摘要

```
## Ship 完成

- 提交: <hash> <message>
- 分支: <branch> → origin/<branch>
- 变更: N files changed, +insertions, -deletions
- E2E: ✅ 通过 / ⚠️ 跳过
- VSIX: <path> (<size>) / 未打包
```

---

## Finish Work（预提交检查清单）

如果只想执行审查不提交，使用 `/finish-work`：

### 清单

- [ ] `tsc --noEmit` 两个包都通过？
- [ ] `pnpm build` 成功？
- [ ] `pnpm test` (core) 通过？
- [ ] 无 `console.log`？
- [ ] 无 `any` 类型？
- [ ] 无本地敏感信息（绝对路径 / token / cookie / auth.json / .codex / .ssh）？
- [ ] esbuild `format: 'esm'`？
- [ ] `pnpm test:agent` 截图正常？
- [ ] `.omm/` 架构文档已同步？

---

## PR 创建（/create-pr）

提交推送后需要创建 PR 时：

```bash
git push -u origin HEAD

gh pr create --title "<type>[scope]: <description>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
- [ ] `tsc --noEmit` passes
- [ ] `pnpm build` succeeds
- [ ] `pnpm test` passes
- [ ] `pnpm test:agent` screenshots verified

## Screenshots
<attach relevant dist/screenshots/*.png>
EOF
)"
```

---

## 安全规则

- **绝不** `git push --force`（除非用户明确要求且不在 main/master）
- **绝不** 提交含密钥的文件
- **绝不** 修改 git config
- **绝不** 使用 `--no-verify` 跳过 hooks
- 如 pre-commit hook 失败，修复后创建 **新提交**，不 amend
- 合并冲突时 **绝不** 自动解决

---

## 与其他命令的关系

```
开发流程:
  编码 → 测试 → /ship → (可选 /create-pr)
                 │
    ┌────────────┼───────────┬──────────────┬─────────────┬──────────┐
    ↓            ↓           ↓              ↓             ↓          ↓
 Phase 1      Phase 1.5   Phase 2       Phase 3      Phase 4     Phase 5
 Review       Arch Docs   Commit        Push         Package     Summary
 ├ tsc        omm write   Conventional  origin/br    VSIX
 ├ build      增量更新     Commits
 ├ test       .omm/
 ├ patterns
 └ E2E smoke
```

| 命令 | 职责 |
|------|------|
| `/finish-work` | 仅审查清单（被 /ship Phase 1 调用） |
| `/ship` | 审查 + 提交 + 推送 + (可选)打包（本命令） |
| `/create-pr` | 推送后创建 GitHub PR |
| `/qa run` | 单次场景 E2E 测试 |
| `/qa-loop` | 测试→修复→回归循环 |
