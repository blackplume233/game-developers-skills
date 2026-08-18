# 游戏白盒拆解标准 Workflow

本文件定义阶段状态机。开始新的拆解案例时完整读取，并从 `assets/templates/workflow-state.json` 复制状态文件到案例根目录。每完成一个阶段，更新产物路径与 Gate 证据，然后运行 `scripts/validate_workflow.py`。不得仅凭叙述把阶段标为通过。

## 状态规则

```text
pending → in_progress → passed
                    └→ blocked → in_progress
条件阶段：pending → skipped（必须写明 reason）
```

- 同时只能有一个 `in_progress` 阶段。
- Required Gate 未通过时不得开始下一个阶段。
- `blocked` 必须记录阻碍、已尝试路线和下一条安全路线。
- `skipped` 只用于条件阶段；不能用它跳过白盒证据门槛。
- 每个 Gate check 都要有本地证据路径、哈希、日志或可复现命令之一。

## P0 学习契约

**Input**：用户目标、游戏/平台/build、可访问材料、关注领域。

**Action**：明确策划问题、期望深度、合法材料边界、预期产物；选择 `recon`、`deep-dive` 或 `complete`。

**Output**：案例状态文件；目标 build 与范围说明。

**Gate**：游戏、build、平台、focus、学习问题、证据范围与案例输出目录全部明确；输出目录不在原游戏目录内。

**Failure route**：缺少 build 或材料时保持 P0 blocked；只能交付准备方案，不宣称白盒完成。

## P1 工具链与解包设计

**Input**：P0 状态、归档头/引擎线索、可用空间。

**Action**：读取 `tool-assisted-extraction.md`；为 catalog、extract、parse、preview、verify 分别发现候选工具；固定来源、版本/commit、许可证和 SHA-256；填写 `extraction-plan.json`。

**Output**：工具候选矩阵；可执行解包方案；最小只读试运行日志。

**Gate**：至少覆盖 catalog/extract/parse/verify 四种角色；每个入选工具都有当前 build 适配依据；已定义分层优先级、空间预算、停止条件、回滚与第二验证路线。

**Failure route**：工具不支持时更换固定源码、第二解析器或最小只读解析器；不得转成黑盒猜测。

## P2 归档目录与隔离提取

**Input**：通过 P1 的 extraction plan 与只读源。

**Action**：先建立全归档清单并保留未知哈希，再做定向提取；基础包和补丁层分别保存；记录源层、逻辑路径、大小、SHA-256 和命令日志。

**Output**：archive catalog、layer manifest、extract manifest、未知条目清单、源文件前后校验。

**Gate**：源目录未被写入；活动范围可由分层清单复建；未知条目未被隐藏；焦点领域取得真实提取物。

**Failure route**：空间不足回到 P1 改为 catalog/selective/parser-direct；源变化立即停止并保留日志。

## P3 结构解析与活动视图

**Input**：P2 分层提取物、类型注册表/格式定义。

**Action**：按补丁优先级生成 active view；批量导出实例、类型、字段、Object/GUID/UserData 引用和解析错误；重复提取或用第二解析器交叉验证。

**Output**：active index、逐资产结构 JSON/页、类型统计、引用边、解析错误与 mismatch 清单。

**Gate**：每个活动资产唯一映射到源层；成功/失败/mismatch 数量明确；关键样本重复输出一致或由第二结构来源确认；逐资产学习页按 asset learning contract 在首屏提供策划功能、真实配置影响、全局位置与职责边界，并写入同源机器索引。

**Failure route**：解析冲突回到 P1 更换 parser/registry；不得丢弃失败样本后声称全量通过。

## P4 焦点系统证据链

**Input**：P3 active view 与用户 focus。

**Action**：围绕一个玩家场景，从入口资产追踪到下游执行资产；记录每条边的来源字段和目标对象；加载对应 AI/技能/动画/渲染参考。

**Output**：至少一条端到端 evidence chain；概念—工程映射表；未知连接清单。

**Gate**：链中每一层都有真实路径、序列化类型、关键字段/引用和证据页；逻辑概念不得替代工程实体。

**Failure route**：引用断裂则留在 P4，扩大定向提取或回到 P3 修复路径解析；不能用名称相似补边。

## P5 运行时/二进制闭环（条件阶段）

**Input**：P4 未能仅靠静态资产回答的运行时问题，以及合法可访问的二进制、日志、反射库或编辑器对象。

**Action**：恢复方法签名、运行时对象、调用边、状态机或字段偏移；把伪代码标为反编译解释，不声称为原源码。

**Output**：方法/地址映射、控制流证据、伪代码、静态资产到运行时消费者的对应表。

**Gate**：每个方法结论绑定 build/hash、签名、地址和复现路径；二进制事实、反编译解释、工程命名、未知分开标注。

**Failure route**：PDB/调用边缺失时记录未知并 `skipped` 或 `blocked`；不得编造正式 API 名。若任务不要求代码级还原，可写明理由后 skipped。

## P6 工程综合与迁移

**Input**：P4 证据链及可选 P5 运行时证据。

**Action**：把每个逻辑概念映射为工程资产、字段、运行时对象、接口和调试输出；再转译为策划体验、配置旋钮、生产成本与自研模块。按 `agent-knowledge-base.md` 与 `mechanism-explanation-contract.md` 把重要概念和结论写入带稳定 ID、规则、运行序列、调参契约、状态、证据和下一探针的机器 seed，并运行 `validate_knowledge_seed.py`。

**Output**：工程执行摘要、系统架构、配置指南、复刻路线、限制清单、`knowledge-seed.json`。

**Gate**：每个重要概念至少包含 `逻辑概念 → 资产路径/类型 → 字段/引用 → 运行时消费者/方法（若已闭合） → 自研对应 → 证据状态`；同时保存通俗定义、真实配置、精确规则、逐步运行序列、输出—消费者绑定、调参直接/下游影响、决定/不决定边界和结构化未知边；`validate_knowledge_seed.py` 通过；每条重要断言只表达一个主张并有 build、证据、限制和下一探针。

**Failure route**：映射缺项回到 P4/P5 补证；不能用抽象类比替代缺失工程信息。

## P7 学习交付与独立审查

**Input**：P6 报告、逐文件证据、读者需求。

**Action**：先用直接说明游戏与工程对象的书名、封面知识契约和行业通用职责地图建立入口，再按“单角色完整 Graph → 总方案 → 子系统 → 运行环节 → 配置实例 → 原始证据”构建报告/WebBook；开篇主节点普通话优先，展开层才显示术语、真实资产和职责边界，线型区分已确认、工程解释与未知；多入口 Web 交付指定主 Book 为视觉真源并填写设计系统清单，共享令牌、字体、语义色与本地 SVG sprite；先使用自然中文写作 Skill 修订成稿，再由零背景行业读者冷读书名、封面、导论和目录，未参与写作的 SubAgent 最后按费曼四步审查事实与可教性；审查记录只进 `.internal/reviews/`；修订到阻断项关闭。

**Output**：读者清单、教学页面、搜索/证据入口、多页面设计系统清单、内部审查记录。

**Gate**：书名和封面在五秒内交代游戏、工程对象、白盒方法与学习结果；零背景行业读者能够复述导论系统地图和目录学习路径；独立 Verdict 通过；无闭卷自测；发布白名单不含内部审查、日志或 Verdict；默认页包含一条当前 build 的完整单角色 Graph，主节点无前置术语，每个核心配置环节可下钻真实资产，旁路与未知边没有冒充已确认连接，展开后焦点仍在视野；每个重要结论可下钻到证据；至少一个贯穿概念按“白话角色 → 真实配置 → 精确规则 → 运行顺序 → 输出消费者 → 调参影响 → 职责/未知边”完整渲染且与 seed 同源；逐资产页先展示策划功能、配置影响和全局位置，再进入字段证据；多入口 Web 的每个页面都引用同一共享设计令牌与本地 SVG sprite，视觉真源和深色证据表面已登记。

**Failure route**：审查不通过则回到 P6；SubAgent 不可用时内部标记未验证，不发布“已验证完成”。

## P8 发布回归与经验沉淀

**Input**：P7 通过的读者产物。

**Action**：运行项目、链接、哈希、发布边界和真实浏览器回归；确认默认入口、搜索、源文件跳转、历史、共享设计资源、设计清单登记视口、控制台和内部路径拒绝；从 P6 seed、机器索引、方法元数据和最终发布白名单构建 Agent Knowledge Base，并按 `agent-access-delivery.md` 生成 llms、OpenAPI、统一 HTTP Agent API 与 stdio MCP，执行 CLI/HTTP/MCP 同源查询回归；只从最终报告提取去敏经验。用户要求一键部署时，按 `portable-package-delivery.md` 生成 learning 或 research Package，并从 Package 自身路径验证 Skill 安装、启动、项目、Agent 接口与哈希。

**Output**：验证报告、启动入口、交付说明、可独立查询的 `knowledge-base/`、llms/OpenAPI/HTTP/MCP 机器入口、本地经验队列及可选网络同步结果。

**Gate**：所有自动检查通过；启动入口实际可用；共享令牌/SVG 静态检查与宽/中/窄屏浏览器回归通过；AKB schema、ID、外键、哈希与内部隔离校验通过；llms 链接、OpenAPI operation、MCP 握手/工具调用通过，CLI/HTTP/MCP 对核心机制、资产关系、方法、未知项和策划俗语返回一致稳定 ID 与证据状态；“[概念]怎么做 / 成立条件 / 怎么调参”一次返回规则、运行序列、调参契约、未知边和证据；Wiki 页面 API 只读发布白名单，`.internal` canary 在所有机器入口和 Package 中命中为零；经验输入不含内部审查或专有原始内容；远程同步仅在用户授权且 `network_safe=true` 时执行。

**Failure route**：页面/哈希失败回到 P7 修复；经验网络同步失败只保留本地队列，不阻塞本次交付。

## 模式所需阶段

| 模式 | 必须通过 | 可条件跳过 | 允许的完成表述 |
|---|---|---|---|
| `recon` | P0–P3 | P4–P8 | “白盒侦察完成”，不得称系统拆解完成 |
| `deep-dive` | P0–P4、P6 | P5、P7–P8（未要求正式交付时） | “专项白盒深挖完成” |
| `complete` | P0–P4、P6–P8 | P5（无代码级问题时） | “白盒拆解完成” |

对比拆解：为每个游戏分别运行一份状态文件，至少达到 `deep-dive`，再对 P6 的同字段工程映射进行比较。
