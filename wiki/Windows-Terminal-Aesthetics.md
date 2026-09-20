# Windows Terminal Aesthetics

`skills/dev-workflow/windows-terminal-aesthetics` — 把 Windows Terminal 的"看起来更黑 / 更磨砂 / 更干净"变成**可测量、可复现、可回滚**的结论。

## Scope

适用于：

- 终端背景不是配色方案（scheme）声明的颜色
- 想做透明、磨砂、亚克力、Mica、无边框（无界窗口）
- 半透明背景下文字发虚 / 有彩边
- 改了 `settings.json` 却"毫无反应"
- 升级 Windows Terminal 后需要确认哪些键还存在
- 想要一份有依据的外观方案对比，而不是"感觉这个更黑"

## Install

```bash
npx skills add blackplume233/game-developers-skills --skill windows-terminal-aesthetics -g -y
```

## The Problem It Solves

终端外观极易靠推理搞错：三层面板合成一个像素值（窗口材质 → 配色背景 × opacity → 标签栏重绘），多数开关互相耦合，而**已安装版本不认识的键会被静默忽略**——设置不生效，却没有任何报错。因此技能的循环固定为：

```text
备份 -> 改配置 -> 对照已安装版本 schema 校验 -> 抓窗口 -> 测量 -> 采纳或回滚
```

## What Gets Measured

三个脚本，全部不依赖第三方库（PNG 由标准库 zlib 解码，无 Pillow/numpy 需求）：

| 脚本 | 作用 |
|---|---|
| `capture-window.ps1` | 用 `PrintWindow(PW_RENDERFULLCONTENT)` 抓窗口**自身**渲染，不受遮挡/焦点影响；支持 `-Geometry` 强制几何、`-Settle` 重采至稳定、`-Activate` 前置并报告是否真的前置、`-CloseMatch` 只关匹配到的那一个窗口 |
| `analyze-capture.py` | 输出 body 实测色（众数 + 均值 + 占比）、逐行色带结构、**标签栏接缝判定**、窗口管理器 1px 边框线（单列）、未绘制边距裁剪后的内容框、文字行连续段；`--json` 供程序消费，`--expect` 做校准 |
| `validate-settings.py` | JSONC 容错解析（注释/尾逗号合法，报错带行号），并对照**按安装版本取到的** schema 校验键名、枚举、类型，标出该版本不认识的键与已废弃键 |

## Measured Facts Worth Knowing

在 Windows 11 + Windows Terminal 1.24.11911.0 + Campbell `#0C0C0C` 上实测（强制几何、稳定态、已校准：opacity 100 时 body 精确等于方案底色）：

- **材质是开关，不是滑杆**：亚克力一开，body 就跳到固定深色 veil 平台（opacity 98→`#222222`，95→`#222222`，90→`#212121`，85→`#202020`）；**再降** opacity 反而把 body 拉回方案色（50→`#181818`，25→`#101010`）。想要"磨砂且更黑"不存在——opacity 100 才会关掉材质、回到纯方案色。
- **材质的签名是抖动**：亚克力下最常用色只占 ~34% 像素（平坦填充是 ~99%），据此可把"材质"与"纯 alpha 混合"区分开。
- **`applicationTheme: dark` 治的是外框**：亮色系统下那 1px 边框线实测 `#FFFFFF`（与 body 差 245），设成 dark 后变 `#2B2B2B`（差 9）。`window.frame` / `unfocusedFrame` 对它**无效**（连 `terminalBackground`、`#00000000` 都试过）。
- **三条被并排实测证伪的假说**：材质色不由系统亮/暗主题决定（light/dark 同色）；不由屏幕位置或壁纸决定（两处位置同色）；`window.frame` 不能改聚焦窗口的边框线。教训是：机理类结论必须"成对测量"，单次测量永远无法证伪机制。
- **没有磨砂强度旋钮**：`acrylicOpacity` 在 1.24 已废弃；schema 里没有模糊半径、饱和度、折射、高光控制——因此 macOS 式"液态玻璃"在此不可复现，技能要求直接说明，而不是继续找不存在的选项。

完整预设与 α 映射表见 [skills/dev-workflow/windows-terminal-aesthetics/references/presets.md](../../skills/dev-workflow/windows-terminal-aesthetics/references/presets.md)，测量协议与被证伪案例见 [references/measurement.md](../../skills/dev-workflow/windows-terminal-aesthetics/references/measurement.md)。

## Boundaries

- `PrintWindow` 展示的是窗口**自身**合成结果：能测材质色调/水平/抖动、body 色、接缝、文字位置，**不能**测 DWM 对窗后桌面的模糊强度。模糊必须肉眼判断，且技能要求如实说明"模糊是目视确认的"。
- 实测数值与 Windows 版本、终端版本、配色方案背景、以及**系统"透明效果"是否开启**绑定；换版本后必须重测，不能沿用旧数字。
- 技能只调外观，不涉及键位、shell、字体安装等与"外观测量"无关的改动。
