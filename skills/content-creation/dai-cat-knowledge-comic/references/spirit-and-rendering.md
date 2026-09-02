# 呆猫神韵、渲染与迭代

本参考用于角色结构已经基本正确，但成图仍显得“像通用萌物、商品毛绒或没有原作神韵”的情况。

## 先写行动意图

生成前先补一句：

```text
呆猫此刻认真想要：{帮助老大完成的具体小事}。
```

眼神、头部朝向、手中道具和身体重心都必须服务于这个意图。没有行动意图的“中性呆脸”容易被模型解释成空洞商品照。

## 单角色校准稿

在生成四格、六格或长条漫前，先做一张单角色、全身、无遮挡、无文字校准稿：

- 只出现一只呆猫。
- 采用轻动作，不采用标准 T Pose、证件照站姿或英雄姿势。
- 至少清楚显示脸盘、官方黑白眼圈/弧形高光、卷曲猫嘴、蓝色连体躯干、米白圆手和短脚。
- 场景保持简单，让问题能归因到角色而不是背景。
- 有用户参考图时逐项对照；无参考图时只验证 Character Lock 和内部神韵，并披露限制。

## 神韵公式

```text
神韵 = 固定呆脸 + 认真意图 + 短小身体的轻微笨拙 + 克制外围特效
```

- **固定呆脸**：巨大黑色圆眼、粗环、白色弧形高光与卷曲猫嘴像同一张贴图；所有动作中不改变开合、视线、嘴角或口型。
- **认真意图**：视线、动作和道具指向同一目标。
- **轻微笨拙**：2–5° 歪头、肩膀收紧、手脚轻微内扣、重心偏移或道具倾斜，只选一两项。
- **球形动作**：圆手保持球形且贴近躯干；靠身体前倾、侧移、踮脚和道具靠近完成动作，不伸出真实长前臂。
- **克制外围特效**：每格最多一个位于脸盘外的问号、汗滴、灯泡、速度线等主特效；不用脸部变形卖萌。

## 渲染目标

```text
restrained in-game character rendering, chunky game-model forms,
matte soft-cloth surfaces, sparse local weave only, a few broad folds,
subtle joint compression, gentle ambient occlusion, soft neutral cutscene lighting
```

避免：

```text
commercial plush product photography, uniform upholstery weave, long fuzzy pile,
clay figurine, glossy plastic, Pixar/Disney look, generic kawaii mascot polish,
cinematic rim-light spectacle
```

“玩偶质感”指游戏角色的柔软块面，不等于真实毛绒商品摄影。若整张脸和身体都覆盖等密度细织纹，判定为渲染漂移。

## 四轮单变量循环

默认最多四轮，每轮重复完整 Character Lock 与禁止项；已经通过的轮次直接跳过：

1. **身份轮**：只纠正蓝色连体头套/躯干、米白脸盘/圆手/短脚、无黄身无领巾，以及官方眼嘴图形；身份失败时阻塞后续轮次。
2. **材质轮**：只纠正毛绒、塑料、黏土、过度织纹或过度电影光照；不改几何和脸谱。
3. **比例轮**：只纠正头身比、梨形身体高度、四肢长度、耳朵和脸盘位置；不改材质与故事。
4. **动作与特效轮**：只纠正头部整体朝向、重心、球形圆手/短脚、道具关系、构图与脸盘外主特效；脸谱完全不变，圆手不得拉成长手臂。

每轮保存：问题、唯一修改变量、结果、分数变化和是否通过。同一维度连续两轮没有可见改善即提前停止；四轮后仍不收敛，也停止生成整页并请求更完整的正面、侧面、面部近景和动作参考图。

## 校准评分

每项 `0=失败，1=勉强，2=通过`：

| 维度 | 2 分标准 |
|---|---|
| 身份锚点 | 蓝色连体头套/躯干、米白脸盘/圆手/短脚、官方眼嘴、无黄身无领巾全部稳定 |
| 比例轮廓 | 头大身小、短肢紧凑，不像高个玩具 |
| 材质渲染 | 游戏资产感明确，无商品毛绒/塑料漂移 |
| 固定脸谱 | 九格叠看时眼睛、白弧与卷曲嘴近似同一张贴图，特效不侵入脸盘 |
| 行动叙事 | 不看文字也能理解角色正在努力做什么，且球形圆手没有拉成长前臂 |

身份锚点为 0 时直接重做。总分低于 8/10 时不进入多格漫画。没有原始参考图时，本评分不包含“原图相似度”。

## 初始提示词增量

在每格提示词的 Character Lock 后追加：

```text
The charm comes from understated sincerity and slightly awkward serious effort,
not a broad smile. Keep the official flat black circular eye graphics, white crescent
highlights and the single continuous curled black cat-mouth mark exactly fixed like
one repeated facial decal in every panel. Express emotion through body weight, head
orientation, limbs, props, composition and at most one anime effect outside the face.
Render as a restrained in-game mascot model with matte soft-cloth forms, sparse
local weave, broad folds and gentle ambient occlusion; never as commercial plush,
clay, glossy plastic, Pixar/Disney, or generic kawaii merchandise.
```

编辑旧图时，使用：

```text
Change only {material | proportions | body action and external effects}. Keep both warm-ivory
paws as spherical forms attached close to the torso with hidden/very short connectors; move
the whole body or prop instead of extending arms. Preserve the exact
identity, official flat eye-and-mouth geometry, continuous blue hood-and-torso color block,
composition and all other approved invariants. Do not redesign the character.
```
