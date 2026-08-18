# Agent 知识库交付规范

完整拆解和正式专项深挖除了读者文档，还必须生成一份本地 Agent Knowledge Base（AKB）。AKB 不是 WebBook 的搜索缓存，而是供后续 Agent 直接查询、引用和继续研究的机器入口。

## 双层交付

- **读者层**：WebBook、教学报告和逐文件页面，负责循序解释。
- **Agent 层**：结构化实体、断言、关系、证据来源和章节切片，负责检索、证据回绑与任务续接。

两层必须共享资产路径、build、SHA-256、方法 ID 和证据路径。不得分别手写两套事实。

## 最小目录契约

```text
knowledge-base/
├── AGENT-ENTRY.md       # Agent 首读入口、查询方法和证据纪律
├── manifest.json        # schema/build/计数/文件哈希/能力声明
├── concepts.jsonl       # 策划概念到工程实体的五段映射
├── claims.jsonl         # 可独立引用的原子断言
├── assets.jsonl         # 活动资产元数据与逐文件证据入口
├── relations.jsonl      # 字段级跨资产引用边
├── methods.jsonl        # 当前 build 的运行时方法元数据
├── sources.jsonl        # 证据来源注册表
├── chunks.jsonl         # 发布语料的标题级语境切片
└── tools/               # 只读查询器和完整性校验器
```

正式 WebBook 还必须按 [agent-access-delivery.md](agent-access-delivery.md) 生成 `llms.txt`、`llms-full.txt`、OpenAPI、统一 HTTP Agent API 和 stdio MCP。CLI、HTTP、MCP 共用 `tools/agent_kb_access.py`，不得各写一套搜索或证据规则。

## 稳定字段

所有记录都应有稳定 `id`、`kind`、`game`、`build` 和 `schema_version`。结论类记录还必须包含：

- `status`: `confirmed | inferred | unknown | self_build`
- `confidence`: `high | medium | low | not_applicable`
- `evidence_ids`: 指向 `sources.jsonl` 的 ID
- `evidence_paths`: 人和 Agent 可直接打开的相对路径
- `limitations`: 当前证据不能证明什么
- `next_probe`: 下一步怎样补证

概念记录应覆盖同一条五段映射：

```text
逻辑概念
  → static_entities（资产路径/RSZ 类型）
  → fields_and_references
  → runtime_methods（或显式 unknown）
  → self_build（数据资产/服务/接口/调试/验收）
```

同时遵循 [concept-teaching-contract.md](concept-teaching-contract.md) 和 [mechanism-explanation-contract.md](mechanism-explanation-contract.md)，为每个核心概念保存 `plain_definition`、`engineering_identity`、`not_this`、`config_shape`、`decision_logic`、`runtime_sequence`、`runtime_contract`、`tuning_contract`、`decides`、`does_not_decide`、`chain_position`、`worked_examples` 和 `confusions`。这些字段分别回答“它是什么”“它怎么做”“怎么调参”和“哪里还没闭合”；五段工程映射回答证据落地问题，缺一不可。

每个 `asset` 记录还必须遵循 [asset-learning-contract.md](asset-learning-contract.md)，保存与逐资产页面同源的 `planning_impact`、`configuration_influence`、`global_position` 和 `basis`。这样 Agent 查询具体文件时先返回策划功能与配置作用，再返回类型、哈希和引用，而不是要求 Agent 从字段名重新猜一遍。

## 构建规则

1. `concepts.jsonl` 与 `claims.jsonl` 来自人工确认的 seed，不从自然语言自动提升为事实。
2. P6 先从 `assets/templates/knowledge-seed.json` 建立 seed，并通过 `validate_knowledge_seed.py`；结构错误不得拖到 P8 才发现。
3. `assets.jsonl`、`relations.jsonl` 和 `methods.jsonl` 从当前 build 的机器索引确定性生成。
4. `chunks.jsonl` 只切分发布白名单内的 canonical reader corpus；标题路径必须保留。
5. 方法记录只保存签名、地址、大小、调用数量和反编译状态等派生元数据，不复制完整反编译正文。
6. 原始专有资源、游戏二进制和完整反编译代码不进入 AKB。
7. `.internal/`、独立审查 Verdict、SubAgent 元数据、生成日志和 Goal 审计不得进入任何 AKB 数据文件或查询结果。
8. build 或源哈希变化时必须重建；旧地址不能沿用为新 build 事实。

## Agent 查询契约

查询器至少支持：

- 关键词跨 `concept/claim/chunk/asset/method` 检索；
- 按 `kind`、`status` 过滤；
- 按稳定 ID 精确读取；
- 按资产 ID 或路径查看入边/出边；
- 以 JSON 输出结果、证据状态、路径和可继续打开的来源。
- “X 怎么做 / 成立条件 / 怎么调参”一次返回 `decision_logic`、`runtime_sequence`、`tuning_contract` 与结构化未知边。
- 支持 `limit/offset/has_more/next_offset` 分页，并提供一次聚合概念、断言、资产、方法、关系、未知项和证据路径的 answer context。
- 使用确定性的同义词与知识图扩展连接策划俗语和工程术语；若未绑定可离线复现的 embedding 模型，不得宣称向量语义检索。

Agent 回答时先引用 `confirmed` 记录；`inferred` 必须保留限定语；`unknown` 只能用于描述缺口；`self_build` 只能作为自研建议，不能反向证明原游戏实现。

## Workflow Gate

- **P6**：生成概念/断言机器真源，重要概念完成五段映射与机制解释契约，并通过 seed validator。
- **P7**：只从最终发布白名单生成 chunks；独立审查仍只在生成期使用，不进入 AKB。
- **P8**：构建 AKB，运行 schema/引用/隔离校验，并至少完成概念、资产路径、运行时方法、未知项，以及“怎么做/条件/调参”三类机制问题查询回归。
- **P8 Agent Access**：验证 llms 链接、OpenAPI operation、HTTP 路由、MCP 握手/工具调用与 CLI 对同一查询返回一致的稳定 ID 和证据状态。

没有可查询的 AKB，`complete` 模式不得通过 P8。正式 `deep-dive` 若承诺后续 Agent 可复用，也适用同一要求。
