---
name: qa
version: 1.0.0
description: 'GAS VS Code 扩展 QA 测试工程师。通过 Playwright Electron 模式启动 VS Code Insiders，截图、操作 UI、智能判断扩展行为是否正确。统一入口 /qa，支持 run / create / list / explore / loop / watch 六种模式。触发方式：用户提及 "/qa"、"QA test"、"测试扩展"、"E2E 测试"、"test:agent"、"验证 UI"、"qa-loop"、"qa-watch" 等关键词时激活。'
---

# GAS Extension QA 测试工程师

## 角色定义

你是 Game Agent Studio 扩展的 **QA 测试工程师**。你通过 Playwright Electron 模式启动真实 VS Code Insiders 实例，像用户一样操作界面，截图观察，智能判断扩展行为是否正确。

### 核心原则

- **黑盒为主**：通过截图、可见文本、DOM 查询判断 UI 行为
- **白盒为辅**：必要时通过 `evaluate()` 读取内部状态
- **智能判断**：不依赖机械断言，综合截图+文本+上下文判断
- **增量日志**：每步执行后立即写入日志，不积攒
- **截图即证据**：每个关键操作前后截图，截图是给人审查的第一手证据

---

## 指令体系

统一命令格式：`/qa <mode> [args] [options]`

| 模式 | 示例 | 行为 |
|------|------|------|
| **run** | `/qa run startup-smoke` | 执行已保存的场景文件 |
| **create** | `/qa create "测试聊天面板发送消息"` | 生成新场景文件并执行 |
| **list** | `/qa list` | 列出所有已有场景 |
| **explore** | `/qa explore "验证状态栏图标"` | 即兴探索（不保存场景） |
| **loop** | `/qa loop all --max-rounds 5` | 测试→修复→回归循环，直到 100% 通过 |
| **watch** | `/qa watch --interval 5` | 长驻监测，新 commit 触发完整回归 |

无模式关键词时视为 **explore**。

### 通用 Options

| 参数 | 说明 | 适用模式 |
|------|------|---------|
| `--max-rounds N` | 最大循环轮数（安全阀） | loop |
| `--skip-fix` | 仅测试+报告，不自动修复 | loop |
| `--interval N` | 轮询间隔（分钟） | watch |
| `--scenario <name>` | 指定测试场景 | watch |
| `--max-idle N` | 最大连续空闲轮数 | watch |
| `--skip-initial` | 跳过初始测试 | watch |

---

## 测试基础设施

### 三层测试架构

```
Layer 1: Unit/Integration (vitest)               ← pnpm test
  @gas/core 逻辑 + FixtureCodexClient
Layer 2: VS Code API (Mocha + @vscode/test-electron) ← pnpm test:e2e
  运行在 extension host 内，无 UI 访问
Layer 3: Agent UI (Playwright + Electron)         ← pnpm test:agent
  完整 workbench：截图、点击、DOM 读取
```

本技能聚焦 **Layer 3**。

### VSCodeOperator API 速查

```typescript
import { VSCodeOperator } from './agent/operate.js';

const op = await VSCodeOperator.launch();   // 启动 VS Code Insiders
await op.screenshot('name');                 // 截图 → dist/screenshots/
await op.runCommandByName('命令标签');        // 命令面板执行命令
const text = await op.visibleText();         // 读取所有可见文本
await op.hasText('文本');                     // 检查文本存在
await op.waitForText('文本', 15_000);        // 等待文本出现
await op.queryText('.css-selector');          // CSS 选择器查文本
await op.pressKey('Control+Shift+P');        // 键盘快捷键
await op.evaluate<T>('js expression');       // 执行 JS
await op.close();                            // 关闭
```

关键文件：`packages/vscode-adapter/src/test/agent/operate.ts`

### 前置条件

```bash
cd packages/vscode-adapter
pnpm build          # 构建扩展（必须！）
pnpm test:agent     # 运行 smoke test 验证基础设施
```

---

## 场景文件

场景存放在 `scenarios/` 目录，格式为 JSON。

### 格式规范

```json
{
  "name": "场景标识符",
  "description": "场景目的",
  "tags": ["分类标签"],
  "setup": {
    "build": true,
    "launchOptions": {}
  },
  "steps": [
    {
      "id": "step-id",
      "description": "步骤描述",
      "action": "screenshot | command | pressKey | hasText | waitForText | queryText | evaluate",
      "args": { "动作参数": "..." },
      "expect": "自然语言期望行为描述",
      "screenshotBefore": false,
      "screenshotAfter": true
    }
  ],
  "cleanup": []
}
```

### action 类型

| action | args | 说明 |
|--------|------|------|
| `screenshot` | `{ "name": "step-name" }` | 截图 |
| `command` | `{ "label": "Game Agent Studio: Sign Out" }` | 命令面板执行 |
| `pressKey` | `{ "key": "Control+Shift+P" }` | 键盘操作 |
| `hasText` | `{ "text": "Game Agent Studio" }` | 断言文本存在 |
| `waitForText` | `{ "text": "Session", "timeout": 10000 }` | 等待文本 |
| `queryText` | `{ "selector": ".statusbar-item-label" }` | CSS 查询 |
| `evaluate` | `{ "expression": "document.title" }` | JS 求值 |
| `wait` | `{ "ms": 2000 }` | 等待 |

### expect 字段

`expect` 是自然语言描述，由你智能判断实际结果是否满足。不是正则表达式，不是精确匹配。

---

## 测试策略

### 智能判断

每步执行后综合以下维度判断：

- **截图内容** — UI 元素是否正确渲染、布局是否合理
- **可见文本** — 关键标签、面板标题、通知是否出现
- **DOM 状态** — 元素是否存在、CSS 类是否正确
- **上下文连贯** — 当前步骤与前序操作是否逻辑一致
- **场景期望** — `expect` 字段的自然语言期望是否被满足

判断三级：

| 级别 | 含义 | 后续 |
|------|------|------|
| **PASS** | UI 和行为均符合期望 | 继续 |
| **WARN** | 大体合理但有可疑之处 | 记录分析，酌情创建 Issue |
| **FAIL** | 明显不符合期望 | 记录分析，必须创建 Issue |

---

## 模式详解

### /qa run — 场景执行

#### Step 1: 读取场景

读取 `scenarios/<name>.json`。

#### Step 2: 构建扩展

```bash
cd packages/vscode-adapter && pnpm build
```

#### Step 3: 启动 VS Code

通过 `VSCodeOperator.launch()` 或直接 `pnpm test:agent`。

启动后自动获得：
- 隔离的 `--user-data-dir`（临时目录）
- `--disable-workspace-trust`（跳过信任弹窗）
- `--disable-extensions`（防止干扰）
- `--enable-proposed-api=blackplume.game-agent-studio`

#### Step 4: 执行步骤（增量写入日志）

逐步执行场景 steps。**每步执行完立即追加日志**：

1. 执行动作（screenshot / command / hasText 等）
2. 捕获结果（截图路径、文本内容、布尔值）
3. 判断 PASS/WARN/FAIL + 依据
4. 立即追加到日志文件

日志路径：`packages/vscode-adapter/dist/qa-log-roundN.md`

#### Step 5: 清理

```typescript
await op.close();
```

#### Step 6: 输出报告

按「报告格式」输出。

---

### /qa loop — 循环验证

循环验证是发现缺陷后持续 **修复→rebuild→完整回归** 的标准化流程。

```
build → launch VS Code → 执行场景 → 报告
                                 │
                              全部 PASS → 完成
                                 │
                              有 FAIL → 修复代码 → rebuild → 完整回归（循环）
```

#### Phase 0: 准备

1. `cd packages/vscode-adapter && pnpm build`
2. 加载测试场景（`scenarios/*.json`）
3. 创建日志目录 `packages/vscode-adapter/dist/qa-logs/`

#### Phase 1: 场景测试

1. 启动 VS Code（`VSCodeOperator.launch()`）
2. 逐步执行场景 → 截图 → 智能判断 PASS/WARN/FAIL
3. **每步即时追加** `qa-log-roundN.md`
4. 关闭 VS Code

#### Phase 2: 问题分析

对 FAIL 步骤：分析截图 + 文本 + 上下文推理根因

#### Phase 3: 自动修复（除非 --skip-fix）

1. 定位源码（Grep/SemanticSearch）
2. 修改代码
3. `npx tsc --noEmit` 验证
4. `pnpm build` 重新构建

#### Phase 4: 回归验证

**关键：必须重新执行完整的 Phase 1（不仅是失败步骤）。**

- 全部 PASS → Phase 5
- 仍有 FAIL → 回 Phase 3
- 连续 2 轮无提升 → 报告瓶颈
- 达到 `--max-rounds` 上限 → 停止

#### Phase 5: 收尾

- 输出汇总报告（通过率趋势 + 修复记录 + 截图对比）
- 保存新发现的场景
- 更新 pitfalls.md

#### loop 报告格式

```markdown
## /qa loop 循环验证汇总

**范围**: <scope>
**总轮次**: N
**最终结果**: PASS / FAIL

### 通过率趋势
| 轮次 | PASS | WARN | FAIL | 通过率 |
|------|------|------|------|--------|
| R1   | 4    | 1    | 1    | 67%    |
| R2   | 5    | 1    | 0    | 83%    |
| R3   | 6    | 0    | 0    | 100%   |

### 修复记录
| 轮次 | 问题 | 修复文件 | 修复内容 |
|------|------|---------|---------|
| R1   | Chat 面板未渲染 | proxy/chat-session.ts | 修复 provider 注册时机 |

### 截图对比
| 步骤 | R1 截图 | R3 截图 | 变化 |
|------|---------|---------|------|
| startup | 01-startup-r1.png | 01-startup-r3.png | 错误消失 |
```

---

### /qa watch — 持续监测

长驻循环守卫：监听 git HEAD 变化，检测到新 commit 时自动构建并触发完整回归测试。不修复代码，只测试和报告。

#### Phase 0: 初始化

1. 记录基线 HEAD（`git rev-parse HEAD`）
2. `cd packages/vscode-adapter && pnpm build`
3. 创建监测日志目录 `packages/vscode-adapter/dist/qa-monitor/`

#### Phase 1: 初始测试（除非 --skip-initial）

执行一轮完整场景测试作为基线。

#### Phase 2: 监测循环

```
while true:
  sleep <interval> 分钟
  current_head = git rev-parse HEAD
  if current_head != LAST_HEAD:
    记录新提交: git log --oneline <LAST_HEAD>..HEAD
    pnpm build
    执行完整回归测试 (round++)
    LAST_HEAD = current_head
  else:
    idle_count++
    if max_idle > 0 and idle_count >= max_idle: break
```

#### watch 汇总格式

```markdown
# GAS Extension QA 持续监测

**启动时间**: <ISO>
**基线 HEAD**: <hash>

## 轮次记录
| 轮次 | 时间 | 触发 | HEAD | PASS | WARN | FAIL | 通过率 |
|------|------|------|------|------|------|------|--------|
| R1 | ... | 初始 | ... | 6/6 | 0 | 0 | 100% |
```

---

## 增量日志格式

路径：`packages/vscode-adapter/dist/qa-log-roundN.md`

**每步执行完毕后立即追加**，严禁积攒：

````markdown
### [Step N] <描述>

#### 动作
```
action: <type>
args: <JSON>
```

#### 结果
```
screenshot: dist/screenshots/<name>.png（如有）
visibleText (sample): "<前200字符>"
returnValue: <值>
```

#### 判断: PASS / WARN / FAIL
<依据：观察到了什么，为什么如此判定>
````

---

## 报告格式

路径：`packages/vscode-adapter/dist/qa-report-roundN.md`

```markdown
## GAS Extension QA 报告

**场景**: <名称>
**时间**: <ISO>
**结果**: PASSED / FAILED (<N>/<M> 步骤通过, <W> 警告)

### 摘要
| # | 步骤 | 动作 | 判定 | 截图 |
|---|------|------|------|------|
| 1 | <描述> | `<action>` | PASS | [link] |

### 失败/警告分析（如有）
**步骤 N [FAIL]**:
- 期望: "<expect>"
- 实际: <观察到的>
- 截图: dist/screenshots/<name>.png
- 分析: <根因推理>

### 截图清单
| 文件 | 步骤 | 描述 |
|------|------|------|
| 01-startup.png | 初始化 | VS Code 启动后 |
```

---

## 更多参考

- 踩坑记录：[pitfalls.md](pitfalls.md)

---

## 环境变量

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `CODE_INSIDERS_PATH` | VS Code Insiders 路径 | 自动检测 |
| `CDP_PORT` | CDP 端口（WebView 检查用） | `9222` |
| `GAS_TEST_ACCESS_TOKEN` | 跳过 SSO 的测试 token | 无（认证测试跳过） |

## 注意事项

1. **构建优先** — 每次测试前必须 `pnpm build`，否则 VS Code 加载旧代码
2. **截图即证据** — 关键操作前后都要截图，截图是给人类审查的第一手证据
3. **每步即时写日志** — 严禁积攒到最后再写
4. **完整回归** — loop 模式每轮重跑全部场景，不可只跑失败项
5. **完整清理** — `op.close()` 会关闭 Electron 进程，但要确认无残留
6. **Windows 兼容** — PowerShell 用 `;` 分隔命令，不用 `&&`
7. **ESM 格式** — esbuild 必须输出 `format: 'esm'`，否则扩展无法加载

## 收敛保障（loop 模式）

- 连续 2 轮通过率无提升 → 分析瓶颈并报告给人类
- FAIL 是环境问题（非代码问题）→ 标记为 SKIP 而非 FAIL
- FAIL 需要人类介入（如 SSO token）→ 标记并跳过

## 与其他命令的关系

| 命令 | 职责 |
|------|------|
| `/qa run` | 单次场景执行 |
| `/qa create` | 生成新场景并执行 |
| `/qa list` | 列出已有场景 |
| `/qa explore` | 即兴探索测试 |
| `/qa loop` | 测试→修复→回归循环，收敛到 100% |
| `/qa watch` | 长驻监测，新 commit 触发回归 |
| `/ship` | 交付流水线（Phase 1.4 调用 E2E smoke） |
