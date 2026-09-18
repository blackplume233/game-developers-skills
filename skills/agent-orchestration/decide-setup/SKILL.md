---
name: decide-setup
version: 1.0.0
description: 安装、配置并验证 pi-decider 决策工具（pi / omp 的 decide 工具，后端为 TypeSafe Jev、OpenRouter Decisions API 或任意 OpenAI 兼容聊天模型）。用于用户要求"装 decide 工具 / 接入 Jev / 配置 TypeSafe 或 OpenRouter 决策后端 / pi-decider 安装 / 决策工具报 no usable backend / 换新设备或新 harness 重装 decide / 检查决策后端凭证与连通性"时。不负责决策用法设计（三原语与四形态见 decide 技能本身）。
---

# Decide Setup（决策工具接入）

把 `decide` 装好、接上后端、验证通过。三类产物分别是：**插件（工具）**、**用法技能（decide）**、**后端凭证**；缺任一项都表现为"工具在了但报 no usable backend"。

## 0. 先判断缺什么

| 现象 | 缺的东西 |
|---|---|
| 命令面板没有 `decide` / 工具调用报 unknown tool | 插件未装或未加载 |
| 报 `No backend is usable` | 凭证未配（见 §3） |
| 工具可用但回答来自聊天模型、标注 `kind chat` | 后端选到了 `llm` 代理，不是真 Jev |
| 只有你能用、别人装了没技能 | 用法技能随包分发，别人需装插件或单独装技能（见 §2C） |

三个后端与其端点（`/decide status` 会把当前解析结果全部列出来）：

| backend | 端点 | 凭证 |
|---|---|---|
| `typesafe` | `POST https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` |
| `openrouter` | `POST https://openrouter.ai/api/alpha/decisions`（模型 `~typesafe/jev-latest`） | `OPENROUTER_API_KEY` |
| `llm` | `POST <baseUrl>/chat/completions`（OpenAI 兼容，兜底代理） | `DECIDER_LLM_API_KEY` + 必须配 model |

## 1. 前置条件

- 宿主为 **pi** 或 **omp**（`decide` 是这两个 harness 的扩展工具）。
- 一个后端凭证：TypeSafe key 或 OpenRouter key（`openrouter` 后端经 OpenRouter 的 Decisions API 调 Jev，无需单独申请 TypeSafe 账号）。
- 首次安装需能访问 npm registry。

## 2. 安装

### 2A. 装插件（推荐：从 registry）

```bash
pi install npm:pi-decider          # pi；加 -l 写进项目级 .pi/settings.json
omp plugin install pi-decider      # omp
```

一条命令同时带来**工具**和**随包分发的 decide 用法技能**。

### 2B. 从源码 checkout 挂载（开发态：改代码即生效）

pi —— 项目级 `.pi/settings.json`（路径相对 `.pi`）：

```json
{
  "extensions": ["../plugins/pi-decider"],
  "skills": ["../plugins/pi-decider/skills"]
}
```

omp —— 必须把**包目录本身**作为扩展入口，才会连包里的 `skills/` 一起加载：

```bash
omp config set extensions '["<abs path>/plugins/pi-decider"]'   # 持久
omp -e "<abs path>/plugins/pi-decider"                          # 单次运行
```

### 2C. 只装用法技能（不给宿主装工具时）

技能本身在仓库里，可单独安装：

```bash
npx skills add blackplume233/game-developers-skills --skill decide-setup -g
```

> **不要同时存在两份**：本地挂载与 registry 安装并用时，同一个工具会注册两次，第二个加载失败并报 `Tool "decide" conflicts with …`。切换安装方式前先移除另一种。

## 3. 配置后端与凭证

### 3A. 引导式（推荐）

```
/decide setup        # 选默认后端 → 选密钥方式（环境变量引用 / 字面值）→ 确认 model 与 baseUrl → 写盘
```

### 3B. 一行命令（可脚本化）

```
/decide set openrouter apiKey $OPENROUTER_API_KEY
/decide set backend openrouter
/decide set typesafe model jev-latest
/decide unset openrouter model            # 删字段；不带字段名则删整块
```

`add` / `set` / `unset` 参数缺失时会依次弹对话框（含当前值），因此交互与脚本化是同一套命令。

### 3C. 环境变量直配（不写配置文件）

```bash
export TYPESAFE_API_KEY=...        # 或 setx（Windows，需新开会话）
export OPENROUTER_API_KEY=...
```

优先级：**配置文件 > 环境变量 > 内置默认**；配置文件每次调用重读，改完不必重载扩展。

### 3D. 配置文件位置（按 harness 自动解析）

| harness | 配置路径 | 目录覆盖变量 |
|---|---|---|
| pi | `~/.pi/agent/decider.json` | `PI_CODING_AGENT_DIR` |
| omp | `~/.omp/agent/decider.json` | `OMP_CODING_AGENT_DIR` |

```json
{
  "backend": "auto",
  "openrouter": {
    "apiKey": "$OPENROUTER_API_KEY",
    "baseUrl": "https://openrouter.ai/api",
    "path": "/alpha/decisions",
    "model": "~typesafe/jev-latest"
  }
}
```

凭证优先用 `"$ENV_VAR"` 引用而不是字面值：字面值会让任何能读该文件的人拿到 key。每个后端块还接受 `timeoutMs`、`maxRetries`、`costPerMTokInput`、`costPerMTokOutput`；`llm` 另有 `temperature`、`maxTokens`、`jsonMode`、`repairAttempts`。

## 4. 验证（按顺序，四步）

1. **看解析结果**：`/decide status` —— 面板会显示每个后端的 key 来源（打码）、端点、模型；无 key 时明确写 `No backend is usable`。
2. **真调用一次**：`/decide question`（形状选 `single`，一路回车即是内置冒烟题），或
   ```
   /decide question is_urgent
   ```
   预期出现一行 header（`backend · 端点说明 · model … → 解析到的版本 · provider · 延迟 · tokens · cost`）加一行答案（如 `is_urgent [noul] 0.87`）。
3. **确认是真 Jev**：header 里 `provider TypeSafe`、`model ~typesafe/jev-latest → typesafe/jev-1.x-YYYYMMDD`；若显示 `kind chat` 或 `proxy decision by a general chat model`，说明落在了 `llm` 后端，回到 §3 配真凭证。
4. **让 agent 调一次**（端到端）：让宿主调用 `decide` 工具做一次判断，确认工具与技能都被加载。

无界面场景（脚本/CI）：用工具而不是命令——`pi -p --tools decide "调用 decide 工具…"`；命令的 `notify` 输出在 print 模式不可见。

## 5. 故障排查

| 症状 | 原因 / 处置 |
|---|---|
| `No backend is usable` | 没配到凭证。`/decide status` 看每个块是 `no key` 还是 `no model`（`llm` 后端缺 model 也算不可用） |
| `Tool "decide" conflicts with …` | 同一插件被两处加载（本地挂载 + registry 安装，或两份拷贝）。只留一处 |
| omp 里改了配置/换了挂载但不生效 | omp **没有 `/reload`**，扩展只在会话启动时加载：**新开会话**。pi 用 `/reload` |
| pi 里扩展/技能不加载 | 项目级资源需项目受信任：首次会询问，或 `pi --approve`，或 `/trust` 持久化 |
| `omp plugin link <path>` 报 EPERM | Windows 符号链接权限不足。改用 `omp plugin install <pkg>` 或 `omp config set extensions '[...]'` |
| 401 / 403 | key 无效或权限不足；OpenRouter 的 Decisions 端点无 key 时返回 401（说明路由存在，不是路径错） |
| 404（OpenRouter） | 只在 ping 具体模型 id 时出现：OpenRouter 目前只有家族别名 `~typesafe/jev-latest`，固定版本号如 `~typesafe/jev-1.13.0` 返回 404 |
| `cost` 缺失 | 聊天后端未上报成本且未配价格；真 Jev 会按 `$0.042/Mtok 输入、输出免费` 计算 |
| 答案里没有 `confidence` | `llm` 代理后端只透传模型给出的 confidence；真 Jev 的 choice/score 一定有 |

## 6. 决策用法速查（细节见包内 decide 技能）

- **三原语**：`noul` = P(yes)；`choice` = 从命名集合选一 + 全分布 + confidence；`score` = 有序等级上的位置（可落在两级之间）。noul≈0.5 是"是非各半"，不是"中等强度"。
- **四形态**：单题；fan-out（一次请求多题并行）；gate（按概率/confidence 阈值路由）；composite（多个 score 归一化后加权合成）。权重与阈值属于调用方代码。
- **路由**：调用级 `backend`/`model`，或**逐题** `questions[i].backend`/`.model`；同后端+同模型的问题合成一个请求，不同批次并行。
- 想读完整用法：装了插件后 `decide` 技能随包分发（pi 里 `/skill:decide`，omp 里 `skill://decide`）；本仓库只负责把它装上并接通。

## 7. 卸载 / 回退

```bash
pi remove npm:pi-decider           # pi（-l 对应项目级）
omp plugin uninstall pi-decider    # omp
```

回退到开发态挂载见 §2B；只清凭证则 `/decide unset openrouter apiKey`。
