# “怎么做”机制解释契约

当用户问“某机制怎么做”“什么时候成立”“我该配什么”“改这个字段影响什么”时，不要只返回术语定义、资产列表或一段运行时概述。对每个核心概念建立同源的结构化机制记录，再由它生成 Book、资产页和 Agent 答案。

## 固定回答顺序

1. **一句话角色**：用普通语言说明该层解决什么问题。
2. **真实配置**：给出当前 build 的资产路径、类型、字段、引用和原值。
3. **精确规则**：优先写成布尔谓词、数值公式、状态转移、排序规则或映射；确实不适用时说明原因，不能硬造公式。
4. **运行顺序**：按触发、输入、处理、输出逐步展开；记录短路、默认值、空列表和失败分支。
5. **输出到消费者**：每个输出与实际消费者绑定，不能分别列两张无法对应的清单。
6. **调参影响**：区分直接影响、下游影响和设计代价；当前值、可用范围或枚举语义未知时分别标记。
7. **职责边界**：明确它不负责什么，以及相邻层从哪里接手。
8. **精确未知边**：写清 `from → to`、缺少什么证据、影响哪条结论和下一探针。

短回答先给 1、3、4、7；如果问题明确包含“配置、调参、改参数”，短回答必须再带第 6 项，不能用篇幅理由省略。Book 概念页完整覆盖八项。字段转储和统计只能放在机制解释之后。

## 结构化字段

核心 concept 在原有教学字段之外增加：

```text
explanation_contract_version: "1.1"
decision_logic {
  kind: boolean_predicate | numeric_formula | state_transition |
        ordering | mapping | passthrough | unknown | not_applicable
  canonical
  terms[] { symbol, meaning, source_locator, status, evidence_paths[] }
  evaluation_order[]
  short_circuit
  limitations[]
  next_probe
}
runtime_sequence[] {
  step_id, order, trigger, inputs[], operation
  outputs[] { value, consumer, effect, consumer_status, next_probe }
  status, evidence_paths[], next_probe
}
tuning_contract {
  availability: present | none | unknown
  items[] {
    control_locator, current_value, value_status
    control_stage, change
    direct_effect, downstream_effect, tradeoff
    effect_status, status, evidence_paths[], next_probe
  }
  reason, limitations[], next_probe
}
chain_position.unknown_edges[] {
  from, to, missing_proof, impact, next_probe, status
}
```

`status`、`value_status`、`effect_status`、`consumer_status` 使用 `confirmed | inferred | unknown | self_build`。复合记录的总 `status` 取其中证据最弱的一项，不能因为字段原值已确认，就把运行时语义也写成 confirmed。`confirmed` 项必须绑定当前 build 的相对证据路径；`unknown` 项必须提供下一探针。证据路径不得指向 `.internal/`、审查或生成日志。

用户在对话中给出的资产名或字段值可以作为本轮分析输入，但在没有 build 身份与可回读相对证据路径时，只能写入临时 input notes，并在正文中标成“用户提供、尚未独立复核”；不要把它写入 seed 的 `confirmed`、`inferred` 或 `unknown` 记录。seed 只登记已取得可回读证据的原游戏事实/推断/断点，或明确标识的 `self_build` 方案。可复现路径存在后再录入并定级，不能把“用户说过”冒充白盒证据。

## 表达规则

- 布尔门槛写出 AND/OR/NOT、排除项、空集合和短路顺序。
- 数值选择写出单项输出、聚合、附加分、优先级门、排序和平局。
- 状态/动作流程写出允许的转移与条件；没有 transition 证据时不把相邻状态串成确定顺序。
- 只有配置字段时，`source_locator` 指向资产字段；恢复运行时消费者后，再补方法/地址，不能用字段名猜代码。
- 调参项必须回答“改大/改小或切换值会直接改变什么”；只有当前原值而无语义时，保留 `value_status=confirmed`，把 `effect_status=unknown`，并填写下一探针。
- `control_stage` 只能取 `enablement | eligibility | selection | scheduling | execution | presentation | unknown`；Priority、CoolTime、Enable 等名字本身不能决定所在阶段，必须由运行时消费者或明确引用证明。不能证明时使用 `unknown` 并建立未知边。
- 已知输出但消费者未知时，保留输出值，将 `consumer` 写为 `unknown`、`consumer_status=unknown` 并提供下一探针，同时建立 `输出 → 未知消费者` 的结构化未知边；不要虚构消费者。
- 失败分支、默认值或重试路径缺证据时，不要伪造一个确定步骤或留空数组。保留最后一个已确认步骤，并为每个会限制结论的断点建立结构化未知边。
- 一个已确认 concept 可以同时包含 unknown edge；不要把整条概念降为 unknown，也不要隐藏局部断点。

## Gate

- P6：`knowledge-seed.json` 通过 `validate_knowledge_seed.py`；核心 concept 的三项机制字段与结构化未知边完整。
- P7：至少一个贯穿案例按固定回答顺序渲染，且与 seed 同源。
- P8：对“[概念]怎么做 / 成立条件 / 怎么调参”执行查询回归，一次返回机制字段、证据路径和未知边；CLI、HTTP、MCP 保持同一稳定 ID 与状态。
