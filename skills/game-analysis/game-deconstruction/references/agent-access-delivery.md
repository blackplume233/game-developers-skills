# Agent 访问层交付规范

用户要求 AI 友好网页、Agent 知识库、标准接口、MCP 或可继续研究的正式 WebBook 时读取本文件。目标不是“让模型抓取 HTML”，而是为人类阅读层和 Agent 证据层提供同源、只读、可发现、可验证的访问方式。

## 必需入口

`complete` 模式和承诺 Agent 复用的 `deep-dive` 必须交付：

```text
explorer/
├── llms.txt
├── llms-full.txt
├── openapi.json
└── agent-access-manifest.json
analysis-project/knowledge-base/
├── manifest.json
├── *.jsonl
└── tools/
    ├── agent_kb_access.py
    ├── query_agent_knowledge_base.py
    ├── validate_agent_knowledge_base.py
    └── agent_mcp_server.py
```

- `llms.txt` 只做发现：说明游戏/build、证据状态、答案包、OpenAPI、MCP、WebBook 与完整语料入口。
- `llms-full.txt` 只拼接发布白名单章节；不得含 `.internal/`、旧稿、审查、Goal 审计或未发布文档。
- `openapi.json` 使用 OpenAPI 3.1，描述实际存在的只读端点；文档和路由必须双向一致。
- `agent-access-manifest.json` 记录 build、corpus hash、公共入口、查询核心、MCP transport、搜索模式和证据状态。
- CLI、HTTP 和 MCP 必须复用同一查询核心，不能各自实现不同的评分、分页或证据规则。
- 回答上下文必须声明 `evidence_path_base`，让 Agent 能把相对证据路径稳定解析到 workspace/project；不得只返回裸路径让调用者猜基准。
- 中文长问题不得把所有二字切片做无约束 OR 检索；先锁定主要领域意图，再对次要意图做小预算补充召回，并把相关 `runtime_methods` 映射到稳定 method 记录。

## HTTP Agent API

网页服务至少提供：

- `GET /api/agent/capabilities`：build、计数、搜索模式、证据与发布边界。
- `GET /api/agent/manifest`：AKB manifest。
- `GET /api/agent/search`：跨概念、断言、资产、关系、方法、来源和章节查询，支持 kind/status/limit/offset。
- `GET /api/agent/record`：按稳定 ID 读取。
- `GET /api/agent/neighbors`：按资产 ID 或逻辑路径查询入边/出边。
- `GET /api/agent/context`：一次返回回答所需的概念、原子断言、资产、方法、关系、未知项和证据路径。

Agent API 不暴露通用文件读取。原始二进制、完整反编译正文、内部审查和生成日志不得通过 canonical Agent 命名空间访问。旧的人类证据查看接口可以保留，但不得在 Agent 发现文档中推荐批量读取 raw/hex。

## 检索契约

默认提供离线、确定性的 `hybrid_lexical_graph`：

1. 统一 Unicode、英文工程词和中文策划词。
2. 使用领域同义词连接“救人/救援/rescue”等表达。
3. 按身份、别名、路径和正文分权重检索。
4. 由 concept ID、asset relation 和 evidence ID 扩展上下文。
5. 排序只决定相关性，绝不改变 `confirmed | inferred | unknown | self_build`。

不得把同义词/图扩展宣传为向量 embedding。只有模型名称、revision、许可证、模型文件哈希、corpus hash、维度、距离算法和离线模型均已登记并完成回归时，才允许声明 `vector_semantic`。没有可再分发模型时保持确定性图检索，不把网络模型下载设为阅读阻塞。

## MCP 契约

提供本地 stdio MCP 服务，默认由 Agent 客户端作为子进程启动，不监听公网。工具至少覆盖：

- `game_deconstruction_search`
- `game_deconstruction_get_record`
- `game_deconstruction_get_context`
- `game_deconstruction_get_asset_neighbors`
- `game_deconstruction_get_manifest`

所有工具标记 `readOnlyHint=true`、`destructiveHint=false`、`idempotentHint=true`、`openWorldHint=false`，返回结构化内容与分页信息。stdout 只承载 MCP 协议；日志写 stderr。运行时使用隔离环境和锁定的官方 SDK；Package 移动后由安装状态或显式 KB 路径重新定位。

## 发布与安全 Gate

- Wiki 页面 API 只能读取发布 manifest 白名单；目录允许范围不能替代逐页白名单。
- `.internal`、`reviews`、`.hgoal`、旧审查文件和生成日志不得出现在 llms、OpenAPI、AKB、HTTP、MCP、Package 清单或哈希清单。
- 本地 HTTP 默认只绑定 loopback；非 loopback 必须显式授权，并重新评估认证、Origin 与暴露面。
- Agent API 元数据不返回机器绝对 workspace 路径。
- 查询参数限制长度、类型、分页和最大返回量；未知 ID 返回明确 404，非法参数返回 400。
- OpenAPI 每个 operation、llms 每个链接和 MCP 每个工具都必须通过实际调用，不以文件存在代替可用性。

## P8 回归

至少用同一组问题分别验证 CLI、HTTP 和 MCP：

1. 一个核心机制，稳定命中 concept/claim。
2. 一条真实资产关系，稳定返回 source/target 路径与字段位置。
3. 一个运行时方法。
4. 一个 `unknown`，保留 limitation 和 next_probe。
5. 一个策划俗语，能通过同义词/图扩展命中工程概念。

三种接口必须返回一致的稳定 ID、build、证据状态和 evidence paths。最后放置不可发布 canary，确认所有机器入口和 Package 均无法检索或读取。
