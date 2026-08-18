# 渲染系统拆解维度

## 分析目标

从真实 Mesh、Material、Texture、Shader/RenderConfig、Light、VFX、PostProcess、Scalability 和平台覆盖资产还原渲染配置与依赖。

## 建立资产基线

记录平台、build、归档层、资产路径、类型、大小、哈希和解析器版本。优先提取代表关卡/角色/技能涉及的 Mesh、材质、纹理、灯光、VFX、Volume 与画质配置。

若 cooked 包只能恢复 shader bytecode、参数表或依赖而不能恢复编辑器图，明确标记“不可逆/未知”，不得用画面相似性补成确定实现。

## 几何与可见性

- 静态/动态网格、实例化、植被、地形、贴花和程序化几何。
- LOD、HLOD、几何虚拟化、遮挡剔除、距离裁剪和流送。
- 导出 bounds、section/material slot、LOD screen size/distance、streaming、cluster/virtualized geometry 和 cull 字段。

## 材质与着色

- PBR 参数、分层材质、材质实例、遮罩、细节纹理、顶点色和贴花。
- 皮肤、头发、眼睛、布料、水、玻璃、雪、泥、湿润和破坏效果。
- 运行时材质参数如何响应技能、伤害、天气、交互和角色状态。
- 自定义光照、卡通渲染、轮廓、Ramp、各向异性或特殊 BRDF 的替代实现。

## 光照、阴影与反射

- 直接光、烘焙光、动态 GI、探针、屏幕空间或光线追踪相关配置、类型和资源引用。
- 主光、局部光、阴影图、接触阴影、胶囊/代理阴影和缓存。
- 反射探针、SSR、平面反射、光线追踪与混合方案。
- 日夜、天气、室内外转换和可破坏场景对光照策略的影响。

## 大气、透明与特效

- 天空、大气散射、高度雾、体积雾、云和局部介质。
- 粒子、Ribbon、网格特效、流体、光照特效和 GPU 模拟。
- OIT、抖动透明、Alpha Test、折射和软粒子的材质、renderer 或 shader 配置字段。
- VFX 与技能阶段、命中、动画事件、材质参数和音效的同步。

## 后处理与时间管线

- 曝光、色调映射、调色、Bloom、景深、运动模糊、暗角和颗粒。
- TAA/TAAU、超分辨率、动态分辨率、锐化和帧生成的时间伪影。
- AO、SSR、屏幕空间阴影与其他依赖历史帧或深度/法线缓冲的效果。
- UI、透明、粒子和后处理的合成顺序线索。

## 性能与伸缩

- 区分 CPU、GPU、显存、带宽、着色、几何、透明和同步瓶颈。
- 对比画质档、分辨率、镜头、对象数、灯光数和特效量的边际成本。
- 记录主机模式、PC 选项和不同平台的功能降级。
- 检查帧时间而非只看平均 FPS；关注尖峰、流送和着色器编译。

## 白盒提取与验证

- 追踪 `world/component → mesh → material slot → material instance → parent/shader → texture/MPC`。
- 追踪 `VFX system → emitter/module → material/mesh/texture → skill/animation event`。
- 追踪 `scalability/device profile/platform config → renderer flag/CVar → quality tier/LOD`。
- 导出 Mesh LOD、纹理尺寸/格式/mip、材质 domain/blend/shading model/参数、Light、Volume、VFX 与 Streaming 字段。
- 用第二预览器验证模型—材质—纹理绑定；画质切换和帧时间测试只验证已提取的 CVar、LOD 和平台覆盖。

## 输出结构

1. 渲染资产清单、类型、路径、源层和哈希。
2. Mesh—材质—纹理—Shader/参数依赖图。
3. 光照、阴影、反射、VFX、Volume 与后处理字段表。
4. 平台、DeviceProfile、画质档和覆盖矩阵。
5. 性能预算与画质伸缩策略。
6. 未解析资源、不可逆 cooked 数据和下一解析路线。
