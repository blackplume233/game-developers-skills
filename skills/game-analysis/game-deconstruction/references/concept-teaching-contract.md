# 工程概念教学契约

当报告或 WebBook 首次引入 Situation、Goal、DecisionPack、ActionInterface、Sensor、Marker、Personality、Formation 等领域术语时，必须先回答“它是什么”，再给类型名、字段和统计。读者不应从资产清单反推概念职责。

## 固定解释顺序

在逐术语页面之前，WebBook 默认入口先用一个真实单角色案例提供“普通话 → 工程概念 → 真实资产”的全局 Graph。读者应先能复述系统为什么分层，再学习 Situation、Goal、DecisionPack、ActionInterface 等名字。Graph 中的工程名只作为二级标签，不得替代普通语言节点标题。

每个核心概念页按以下顺序组织：

1. **通俗定义**：用一句不依赖本游戏术语的话说明它解决什么工程问题。
2. **工程身份**：分别列出静态配置资产、一次运行时求值/实例、运行时容器或服务；同一术语指向多个实体时必须拆开。
3. **它不是什么**：与相邻层消歧，明确不能把它误认为哪些常见系统。
4. **具体配置长什么样**：用一个当前 build 的真实资产画缩进对象树，展示根类型、数组、对象引用、跨文件引用和代表原值。
5. **精确规则**：按 [mechanism-explanation-contract.md](mechanism-explanation-contract.md) 写出布尔谓词、数值公式、状态转移、排序、映射或显式不适用，并解释符号、求值顺序、短路与默认行为。
6. **运行时序列**：逐步绑定触发、输入、处理、输出与消费者；普通 `输入 → 处理 → 输出 → 消费者 → 更新时机/预算` 摘要继续保留，但不能替代步骤证据。
7. **调参影响**：从真实字段或引用说明当前值、改变方式、直接影响、下游影响与代价；语义未知时提供下一探针。
8. **决定什么**：只写该层直接负责的运行时决策，以及经过哪条已确认链路间接影响下游。
9. **不决定什么**：明确它不负责的上游输入、下游选择、动作、动画或渲染结果。
10. **完整链位置**：用实线表示真实引用/调用，用虚线表示工程推断；未知边必须结构化记录起点、终点、缺失证据、影响和下一探针。
11. **真实实例**：把配置原值、运行时含义和不能证明的部分放在同一个案例中。
12. **自研对应**：给出数据资产、运行时服务、接口、调试输出和验收；固定标为自研迁移。

## 证据纪律

- 类型、字段、数组、引用、原值、方法地址和直接控制流可标为已确认。
- “事实缓存”“问题入口”“动作协议”等便于学习的抽象应标为工程解释，不能冒充原命名。
- 配置字段存在，不等于它的完整运行时语义已经恢复；字段名相似也不能补上调用边。
- 文件名编号、资产字段 ID、运行时偏移中的标识必须分别保存；没有映射证据时不能写成同一个 ID。
- 分批更新存在时，不把“每次调用配额”写成“必然每帧”，也不承诺配置变化同帧可见。
- “未知”必须随当前证据更新，不能永久复制旧报告：评分公式或动画映射一旦闭合，Book、逐资产页、Agent KB 的 concept/claim 和限制章节应在同一次构建中去除对应旧未知。
- 局部闭合必须写出准确断点。例如可以确认 `状态 → MotionBank → Clip → 事件帧`，同时保留 `ActionInterface/Command → 具体状态` 的调度边，以及 `事件 → 玩法副作用处理器` 为未知；不得用一个笼统的“动画已还原”掩盖两者。

## Agent 知识库字段

每个核心 `concept` 除工程 crosswalk 外，还必须提供：

```text
plain_definition
engineering_identity
not_this[]
config_shape
runtime_contract { inputs[], process[], outputs[], consumers[], update_timing }
decision_logic { kind, canonical, terms[], evaluation_order[], short_circuit, limitations[], next_probe }
runtime_sequence[] { step_id, order, trigger, inputs[], operation, outputs[{value, consumer, effect}], status, evidence_paths[], next_probe }
tuning_contract { availability, items[], reason, limitations[], next_probe }
decides[]
does_not_decide[]
chain_position { upstream[], current, downstream[], unknown_edges[{from, to, missing_proof, impact, next_probe, status}] }
worked_examples[]
confusions[]
```

这样 Agent 回答“它是什么”“配置长什么样”“运行时决定什么”时，应优先读取结构化概念记录，而不是自行拼接章节切片。

## 交付 Gate

- 核心术语在首屏先出现通俗定义，不能先出现统计和字段表。
- 至少一个真实配置树能回到逐文件证据页。
- 运行时契约明确区分静态配置、一次求值/实例和持续运行时状态。
- “决定什么”和“不决定什么”均非空。
- Agent KB 精确 ID 查询能一次返回定义、配置外形、运行时契约与职责边界。
- `validate_knowledge_seed.py` 通过；规则、运行步骤、调参项和未知边的嵌套字段均可验证。
- 对“怎么做 / 成立条件 / 怎么调参”的查询一次返回机制字段与证据，不要求 Agent 从章节切片重新推理。
- 独立费曼审查只检查解释是否可复述、证据边界是否准确；不在读者页面添加自测或审查结果。
- 默认入口的单角色 Graph 能把每个核心概念对齐到至少一份当前 build 的真实资产；多资产环节显示实际数量和职责，不虚构“一角色一 AI 文件”。
