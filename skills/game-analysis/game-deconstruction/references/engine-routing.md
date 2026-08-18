# 引擎与证据条件路由

## 先按访问条件选择路径

| 条件 | 优先动作 | 可得结论 |
|---|---|---|
| 只有实机或录像 | 建立可重复场景、逐帧记录、画质与性能对比 | 行为、时序、视觉特征和实现假设 |
| 有公开资料 | 将开发者演讲、官方文档和补丁说明与实机交叉验证 | 架构线索、版本变化和设计意图 |
| 有已授权资产/项目 | 只读盘点类型、依赖、配置、图和运行时调试信息 | 配置结构、资产关系和部分实现事实 |
| 有已授权源码 | 从入口、数据定义、运行时链路和调试工具验证模型 | 实现级事实与可追溯调用关系 |

访问等级不同的结论不能混写；报告必须说明每条发现基于哪种条件。

## Unreal Engine 线索

仅在有证据时检查：Behavior Tree/Blackboard、StateTree、EQS、AI Perception、GAS、DataAsset/DataTable、Gameplay Tags、AnimBP、Montage、Control Rig、Niagara、材质实例、Lumen、Nanite 和 TSR 等。

优先调用 `unreal-dev-assistant` 读取真实项目或运行时信息。功能外观相似不代表项目一定使用对应 UE 模块。

## Unity 线索

仅在有证据时检查：MonoBehaviour/ECS、ScriptableObject、Animator/Playable、NavMesh、Behavior/Utility 插件、URP/HDRP、Shader Graph、VFX Graph 和 Addressables 等。

区分 Unity 原生功能、Asset Store 插件和团队自研框架；不要从文件名或画面风格单独判定。

## 自研或未知引擎

保持引擎无关词汇：感知、决策、能力定义、状态、事件、动画图、帧管线、资源流送和调试数据。先建立输入—状态—输出模型，再用文件格式、工具界面、开发者资料或运行时证据判断具体技术。

## 引擎判断输出

列出：

1. 候选引擎或框架。
2. 支持证据及等级。
3. 冲突证据。
4. 其他可解释同一现象的方案。
5. 能区分候选方案的下一步验证。

若证据不足，明确写“引擎未知”；这不会阻止完成系统层拆解。
