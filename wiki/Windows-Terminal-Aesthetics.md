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
| `capture-window.ps1` | 用 `PrintWindow(PW_RENDERFULLCONTENT)` 抓窗口**自身**渲染，不受遮挡/焦点影响；支持 `-Geometry` 强制几何、`-Settle` 重采至稳定、`-Activate` 前置并报告是否真的前置（用 `AttachThreadInput` 绕过后台进程的前台锁）、`-CloseMatch` 只关匹配到的那一个窗口；`-Screen` 则抓**真实屏幕合成**（含合成器那层模糊），用于回答"浅色背景下会怎样" |
| `white-backdrop.ps1` | 铺一块不透明白底（默认 `White`，可 `-Color`），作为半透窗口的固定背景；自身**不抢前台**（继承 `Form` 覆写 `ShowWithoutActivation`），配合 `-Screen` 使用 |
| `analyze-capture.py` | 输出 body 实测色（众数 + 均值 + 占比）、逐行色带结构、**标签栏接缝判定**、窗口管理器 1px 边框线（单列）、未绘制边距裁剪后的内容框、文字行连续段；`--json` 供程序消费，`--expect` 做校准 |
| `validate-settings.py` | JSONC 容错解析（注释/尾逗号合法，报错带行号），并对照**按安装版本取到的** schema 校验键名、枚举、类型，标出该版本不认识的键与已废弃键 |

## Measured Facts Worth Knowing

在 Windows 11 + Windows Terminal 1.24.11911.0 + Campbell `#0C0C0C` 上实测（强制几何、稳定态、已校准：opacity 100 时 body 精确等于方案底色）：

- **材质是开关，不是滑杆**：亚克力一开，body 就跳到固定深色 veil 平台（opacity 98→`#222222`，95→`#222222`，90→`#212121`，85→`#202020`）；**再降** opacity 反而把 body 拉回方案色（50→`#181818`，25→`#101010`）。想要"磨砂且更黑"不存在——opacity 100 才会关掉材质、回到纯方案色。
- **材质的签名是抖动**：亚克力下最常用色只占 ~34% 像素（平坦填充是 ~99%），据此可把"材质"与"纯 alpha 混合"区分开。
- **`applicationTheme: dark` 治的是外框**：亮色系统下那 1px 边框线实测 `#FFFFFF`（与 body 差 245），设成 dark 后变 `#2B2B2B`（差 9）。`window.frame` / `unfocusedFrame` 对它**无效**（连 `terminalBackground`、`#00000000` 都试过）。
- **三条被并排实测证伪的假说**：材质色不由系统亮/暗主题决定（light/dark 同色）；不由屏幕位置或壁纸决定（两处位置同色）；`window.frame` 不能改聚焦窗口的边框线。教训是：机理类结论必须"成对测量"，单次测量永远无法证伪机制。
- **"浅色背景下变灰"是可量化、可缓解的**：纯白底真实合成下，亚克力 50 的 body 是 `#727275`、文字对比度 4.7:1；85/90 则分别 `#242425`/`#2D2D2D`、8.8/8.4:1（纯黑底色 + 高 opacity）。schema 里**没有任何按背景补偿的键**：唯一旋钮是 opacity，唯一压低地板的手段是把方案底色改成 `#000000`。要"任何壁纸都必须纯黑"，只能 opacity 100（材质关闭）。
- **没有磨砂强度旋钮**：`acrylicOpacity` 在 1.24 已废弃；schema 里没有模糊半径、饱和度、折射、高光控制——因此 macOS 式"液态玻璃"在此不可复现，技能要求直接说明，而不是继续找不存在的选项。

完整预设与 α 映射表见 [skills/dev-workflow/windows-terminal-aesthetics/references/presets.md](../../skills/dev-workflow/windows-terminal-aesthetics/references/presets.md)，测量协议与被证伪案例见 [references/measurement.md](../../skills/dev-workflow/windows-terminal-aesthetics/references/measurement.md)。

## 当前效果（可直接抄）

技能实测基线用的就是下面这套：**纯黑底色 + 亚克力 90**，目标是"黑窗 + 霜，且换个亮色壁纸也不塌成灰"。

```jsonc
{
    "schemes": [{
        // 抄本机安装版自带方案的颜色（这里即 Campbell），只改 background
        "name": "Obsidian Black",
        "background": "#000000", "foreground": "#CCCCCC", "cursorColor": "#FFFFFF",
        "black": "#0C0C0C", "red": "#C50F1F", "green": "#13A10E", "yellow": "#C19C00",
        "blue": "#0037DA", "purple": "#881798", "cyan": "#3A96DD", "white": "#CCCCCC",
        "brightBlack": "#767676", "brightRed": "#E74856", "brightGreen": "#16C60C",
        "brightYellow": "#F9F1A5", "brightBlue": "#3B78FF", "brightPurple": "#B4009E",
        "brightCyan": "#61D6D6", "brightWhite": "#F2F2F2"
    }],
    "themes": [{
        "name": "seamless",
        "window": { "applicationTheme": "dark" },
        "tabRow": { "background": "terminalBackground", "unfocusedBackground": "terminalBackground" },
        "tab": { "background": "terminalBackground", "unfocusedBackground": "#00000000", "showCloseButton": "hover" }
    }],
    "theme": "seamless",
    "profiles": { "defaults": {
        "colorScheme": "Obsidian Black",
        "useAcrylic": true,
        "opacity": 90,
        "antialiasingMode": "grayscale",
        "intenseTextStyle": "bold",
        "adjustIndistinguishableColors": "always",
        "padding": "0",
        "cursorShape": "filledBox",
        "scrollbarState": "hidden",
        "font": { "face": "Maple Mono NF CN", "size": 12,
                  "features": { "calt": 1, "zero": 1, "cv01": 1, "cv03": 1, "cv04": 1, "ss07": 1 } }
    } }
}
```

实测（1.24.11911.0，强制几何、稳定态、聚焦、空面板；对比度为 `#CCCCCC` 文字 vs 实测 body）：

| 配置 | 窗口自身合成 | 纯白底真实合成 | 白底对比度 |
|---|---|---|---|
| **本预设**（`#000000` + 亚克力 90） | `#212121` | `#2D2D2D` rgb(46,47,46) | **8.4:1** |
| 同上，亚克力 85 | `#202020` | `#242425` rgb(42,43,45) | 8.8:1 |
| Campbell `#0C0C0C` + 亚克力 50 | `#181818` | `#727275` rgb(84,87,90) | 4.7:1 |

两次独立抓取逐字节一致（spread 0）。注意方向：**提高** opacity 反而让亮背景下的 body 略亮（85 是 `#242425`，90 是 `#2D2D2D`），因为材质自身的 veil 随之变强——和上文 α 表的反直觉是同一机制。

两条关键值各自负责什么：

- `background: #000000`：玻璃画在方案底色之上（opacity 100 时 body 精确等于方案底色，这是全部测量的校准点），所以方案色就是材质的地板；**压低地板是唯一对"所有背景"同时生效的改动**。
- `opacity: 90`：高到背景抢不走主导权。同一窗口在纯白底上 50 时测得 `#727275`、文字对比度仅 4.7:1，已经不算黑窗；85-95 都可用，低于 ~80 就由壁纸决定观感了。
- 其余是"清晰度"而非颜色：灰度抗锯齿（材质上不再叠彩色描边）、`intenseTextStyle: bold`（保色相而不提亮）、`padding: 0`（不留内侧空白带）。

## 第二个预设：无材质半透

上面那套的前提是**这台机器真的给得出材质**。实测里遇到另一种机器：DWM 拒绝提供背景材质，于是亚克力不是"少一点模糊"，而是把面板推到**更不透明**的一档——`useAcrylic: true` 在 opacity 85 与 60 下都测出与方案底色**完全一致**的 `#1E1E2E`，比关掉亚克力还实。

```jsonc
"themes": [{
    "name": "translucent",
    "window": { "applicationTheme": "dark", "useMica": false },
    "tabRow": { "background": "#1E1E2ECC", "unfocusedBackground": "#1E1E2EAA" },
    "tab": { "background": "terminalBackground", "unfocusedBackground": "#00000000", "showCloseButton": "hover" }
}],
"theme": "translucent",
"profiles": { "defaults": {
    "useAcrylic": false,
    "opacity": 90,
    "unfocusedAppearance": { "opacity": 82 },
    "antialiasingMode": "grayscale"
} }
```

屏幕合成实测（窗口矩形抓屏、含背景；底层由 `(body − opacity × 方案色) / (1 − opacity)` 反推）：

| 配置 | 实测 body | 反推底层 |
|---|---|---|
| opacity 100（校准） | `#1E1E2E` | 无——精确等于方案底色 |
| opacity 85，**Mica 开** | `#1F1F2C` | `#252521`——是 Mica，不是桌面 |
| opacity 90，Mica 关 | `#222231` | `#46464C`——背后那个灰色窗口 |
| opacity 85，Mica 关 | `#1D1D2A` | `#171713`——背后的深色桌面 |
| opacity 0，Mica 开 | `#202020` 平铺 | Mica 的纯色降级值；同一矩形窗口最小化后是 `#121212` + `#067AB0` |

两条结论：

- **材质关掉之后，opacity 才是相对真实背景的 alpha 混合**：反推底层跟着窗后内容走（灰窗口 `#46464C`、深色桌面 `#171713`），而不是钉在某个固定档位。同一 opacity 在两行读数不同，是背景变了，不是设置变了。
- **Mica 会把桌面挡死**。开着 Mica 时反推底层恒为 `#252521`；`opacity: 0` 时整块测得 `#202020`，而同一矩形在窗口最小化后是 `#121212` / `#067AB0`。面板透明是对 Mica 求值，所以"Mica 开着的透明窗"永远看不到真正的窗后内容——想真透，`useMica` 必须为 false。

### 诊断"材质缺失"三连（按顺序）

1. `opacity: 0` + `useMica: true`：body 平整单色，而同一矩形最小化后是**不同的、有变化的**桌面 → 材质在画纯色降级值。
2. `opacity: 85`，亚克力**关 vs 开**：关时半透、开时精确等于方案底色 → 材质不可用。材质"存在但坏掉"仍然报 on，只能靠对比，不能靠看设置。
3. 再排除可控原因：透明效果开启（`UISettings.AdvancedEffectsEnabled`）、节能模式关闭且接电源、非 RDP 会话、无远程/串流软件安装的虚拟显示适配器、显卡驱动已装。

本次实测的机器上第 3 步**全部通过**，材质依然只画纯色，因此**根因未确定**——能带走的是上面的诊断，而不是某个猜测出来的原因。同类现象上游记录在 `microsoft/terminal` issue 18189。

## Boundaries

- `PrintWindow` 展示的是窗口**自身**合成结果：能测材质色调/水平/抖动、body 色、接缝、文字位置，**不能**测 DWM 对窗后桌面的模糊强度。模糊必须肉眼判断，且技能要求如实说明"模糊是目视确认的"。
- 实测数值与 Windows 版本、终端版本、配色方案背景、以及**系统"透明效果"是否开启**绑定；换版本后必须重测，不能沿用旧数字。
- 技能只调外观，不涉及键位、shell、字体安装等与"外观测量"无关的改动。
