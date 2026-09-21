# Game Developers Skills Wiki

## Navigation

- [Home](wiki/Home.md)
- [Installation](wiki/Installation.md)
- [Skill Publishing](wiki/Skill-Publishing.md)
- [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md)
- [Maintenance Rules](wiki/Maintenance-Rules.md)
- [skills.sh 收录与页面维护](wiki/SkillsSH-Listing.md)
- [Game Analysis Skills](wiki/Game-Analysis.md)
- [Windows Terminal Aesthetics](wiki/Windows-Terminal-Aesthetics.md)

## Purpose

This file is the root entry point for the in-repository Wiki. Durable workflow
details live under `wiki/` as separate pages so the repository has a real Wiki
surface instead of one growing document.

## Page Map

| Page | Scope |
|------|-------|
| [Home](wiki/Home.md) | Repository overview, page navigation, and first-time orientation |
| [Installation](wiki/Installation.md) | Normal installs, default repository behavior, skill bundles, install troubleshooting, and the authenticated path for genuinely private repositories |
| [Skill Publishing](wiki/Skill-Publishing.md) | Release gates, version checks, privacy audit, current skill notes including Auto Goal frontmatter state and QA plan-first/user-reproducible principles, changelog, commit, and push |
| [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md) | External skill repositories managed as submodules |
| [Maintenance Rules](wiki/Maintenance-Rules.md) | Documentation freshness, repository layout, local updates, and operating rules |
| [skills.sh 收录与页面维护](wiki/SkillsSH-Listing.md) | 普通个人仓库收录、页面分组、遥测触发与缓存复查 |
| [Game Analysis Skills](wiki/Game-Analysis.md) | 游戏白盒拆解技能的适用范围、机制解释契约、安装与交付边界 |
| [Windows Terminal Aesthetics](wiki/Windows-Terminal-Aesthetics.md) | Windows Terminal 外观调优技能的测量协议、实测预设、可选参数面与能力边界 |

## Recent Additions

- `windows-terminal-aesthetics` v1.0.4 -> v1.1.0: 新增 **Translucent Dark** 预设，补齐此前没覆盖的两个场景——机器给不出背景材质，以及"想看穿到真实桌面"而不是材质薄纱。做法是两把材质开关都关掉（`useAcrylic: false` + `useMica: false`），标签栏改自带 RGBA 底色（`#1E1E2ECC` / `#1E1E2EAA`，因为已无底层可透），`opacity: 90` + `unfocusedAppearance.opacity: 82`。同时记下**材质可能"在 schema 里、却不在这台机器上"**：实测 `useAcrylic: true` 在 opacity 85 与 60 下都精确画出方案底色 `#1E1E2E`，比关掉亚克力**还实**；Mica 在 `opacity: 0` 时整块平铺 `#202020`，而同一矩形窗口最小化后是 `#121212` / `#067AB0`——面板透明是对 Mica 求值，想真透必须 `useMica: false`。附三连诊断（Mica `opacity: 0` → 亚克力关/开对比 → 排除可控原因），并注明本次机器上第 3 步全部通过、**根因未确定**；同类现象记录于 `microsoft/terminal` issue 18189。新预设的 23 个键已过 `validate-settings.py`（v1.24.11911.0）。仓库 wiki 页同步新增「第二个预设：无材质半透」一节。

- `windows-terminal-aesthetics` v1.0.3 -> v1.0.4: 把"当前效果"固化成**可直接抄的预设**——`references/presets.md` 新增完整的 **Obsidian Black** 预设(Campbell 色板 + `background: #000000` + 亚克力 `opacity: 90` + 灰度抗锯齿/粗体强调/零内边距,含 seamless theme 的 `tabRow`/`tab`),并补上该预设**自身**的实测:窗口自身合成 `#212121`,纯白底真实合成 `#2D2D2D` rgb(46,47,46)、`#CCCCCC` 文字对比度 **8.4:1**,两次独立抓取逐字节一致(spread 0)。仓库 wiki 页同步新增「当前效果(可直接抄)」一节,并把 `-Screen`、`white-backdrop.ps1` 写进工具表与实测事实。

- `windows-terminal-aesthetics` v1.0.2 -> v1.0.3: 补上"看得见的另一半"——新增 `capture-window.ps1 -Screen`(真实屏幕合成,含合成器那层模糊)与 `white-backdrop.ps1`(不透明白色底板,且不抢前台),把"浅色背景效果差"量化成数字:纯白底上 opacity 50 的 body 是 `#727275`、文字对比度跌到 4.7:1,opacity 85 则 `#242425`、8.8:1;结论是 opacity 是唯一旋钮、把 scheme 底色降到 `#000000` 是唯一能压低地板的手段。同时修掉两个静默缺陷:后台进程里 `SetForegroundWindow` 被前台锁拒绝会让 `-Screen` 拍到**别的东西**(整轮颜色全是 `#FFFFFF`),现改用 `AttachThreadInput` 强制激活并把 `focused: NO` 定义为失败;`ShowWithoutActivation` 是 protected 属性,必须继承 `Form` 而不能赋 值。另记录 `useMica`/`applicationTheme` 属于 `themes[].window`——写到顶层 `window` 会被静默忽略,那一轮"Mica"其实什么都没测。

- `windows-terminal-aesthetics` v1.0.1 -> v1.0.2: 记下「抓到的 body 色 ≠ 亮度」——半透下窗后桌面的模糊才是主导项,而它**不在** PrintWindow 抓屏里(实测 opacity 50 的 `#181818` 比 opacity 85 的 `#202020` 更暗,屏幕上却更灰)。据此把「曜黑 + 霜」的实用区间定为 **85-95**,50 及以下归为「灰玻璃」的另一种观感,坑位写进 Measured Pitfalls。

- `windows-terminal-aesthetics` v1.0.0 -> v1.0.1: 删掉 `opacity` 的一处过度解读——PrintWindow 根本测不到"透出多少桌面"，且原文与 `opacity` 的语义相矛盾（更低就是更透，只是合成后的 body 值不同）；补上磨砂"半透"端的实测预设（opacity 50 → `#181818`、25 → `#101010`），并把"材质/opacity 变更对**已打开窗口实时生效**（实测 #202020 → #0A0A0A → #202020），无需重启"写进工作流。
- `windows-terminal-aesthetics` v1.0.0 (Dev Workflow): Windows Terminal 外观调优技能，把"看起来更黑/更磨砂"变成可测量的结论——`capture-window.ps1` 用 PrintWindow 抓窗口自身渲染（抗遮挡），`analyze-capture.py` 给出 body 色、色带结构、标签栏接缝、未绘制边距裁剪与文字行段，`validate-settings.py` 把 settings.json 对照**已安装版本**的 schema 校验。附实测预设与 α 映射表，并记录三条被并排实测证伪的材质假说。见 [wiki 页面](wiki/Windows-Terminal-Aesthetics.md)。
- `character-skill-forge` v1.0.0 (Skill Management): 把已授权的任意角色参考图转化为角色专属知识漫画 Skill；先分层记录证据与未知项，再建立身份、表情、肢体和渲染四类角色锁，通过单角色锚点、九宫格压力测试及四格真实试例完成有限单变量校准，并区分本地创建、安装、提交与发布授权。
- `dai-cat-knowledge-comic` v1.3.2 (Content Creation): 固定官方黑白眼圈、白弧高光与卷曲猫嘴；米白前肢锁定为贴近蓝色躯干的球形圆手，禁止长前臂、肘部、手腕和手指；情绪由身体重心、道具、构图及脸盘外单一动漫特效表达。
- `skill-repo-manager` v1.5.2: 升级为路由式主文案（Dispatch 路由表分诊 Finder/Publisher）；Finder 主动按需检索技能——本地缓存优先、缺失问用户、用户不告知则自远端下载安装；新增 `refresh_cache.py` 本地缓存脚本；以远端 URL 为稳定锚点、不写死本地绝对路径。
- `obscura` v1.2.1 (Dev Workflow): Rust 开源无头浏览器技能，网页抓取/截图/PDF/AI 自动化/搜索（含一键 `search.sh`），内置一键安装脚本 `install.sh`，见 [skills/dev-workflow/obscura](skills/dev-workflow/obscura/)。

## Maintenance Contract

Keep `README.md`, this `WIKI.md`, and the relevant `wiki/*.md` page in sync
when repository behavior changes. The root `WIKI.md` should stay an index; do
not move long process documentation back into this file.

Adding or changing a skill touches four places, and the freshness guard below
requires `README.md` and `WIKI.md` to move together with the skill:

1. `skills/<category>/<skill>/` — the skill itself (frontmatter needs `version`)
2. `README.md` — the category table row, the bulk-install `--skill` list, and the layout tree
3. `skills.sh.json` — the skill listed under its grouping (`sync_skills_sh.py --check` must pass)
4. `wiki/Skill-Publishing.md` — a short note in "Current Skill Notes" when behavior matters

Run the documentation freshness guard before committing behavior-changing
changes:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```
