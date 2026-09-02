# Game Developers Skills Wiki

## Navigation

- [Home](wiki/Home.md)
- [Installation](wiki/Installation.md)
- [Skill Publishing](wiki/Skill-Publishing.md)
- [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md)
- [Maintenance Rules](wiki/Maintenance-Rules.md)
- [skills.sh 收录与页面维护](wiki/SkillsSH-Listing.md)
- [Game Analysis Skills](wiki/Game-Analysis.md)

## Purpose

This file is the root entry point for the in-repository Wiki. Durable workflow
details live under `wiki/` as separate pages so the repository has a real Wiki
surface instead of one growing document.

## Page Map

| Page | Scope |
|------|-------|
| [Home](wiki/Home.md) | Repository overview, page navigation, and first-time orientation |
| [Installation](wiki/Installation.md) | Normal installs, default repository behavior, skill bundles, private repository authentication, and troubleshooting |
| [Skill Publishing](wiki/Skill-Publishing.md) | Release gates, version checks, privacy audit, current skill notes including Auto Goal frontmatter state and QA plan-first/user-reproducible principles, changelog, commit, and push |
| [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md) | External skill repositories managed as submodules |
| [Maintenance Rules](wiki/Maintenance-Rules.md) | Documentation freshness, repository layout, local updates, and operating rules |
| [skills.sh 收录与页面维护](wiki/SkillsSH-Listing.md) | 普通个人仓库收录、页面分组、遥测触发与缓存复查 |
| [Game Analysis Skills](wiki/Game-Analysis.md) | 游戏白盒拆解技能的适用范围、机制解释契约、安装与交付边界 |

## Recent Additions

- `dai-cat-knowledge-comic` v1.3.2 (Content Creation): 固定官方黑白眼圈、白弧高光与卷曲猫嘴；米白前肢锁定为贴近蓝色躯干的球形圆手，禁止长前臂、肘部、手腕和手指；情绪由身体重心、道具、构图及脸盘外单一动漫特效表达。
- `skill-repo-manager` v1.5.2: 升级为路由式主文案（Dispatch 路由表分诊 Finder/Publisher）；Finder 主动按需检索技能——本地缓存优先、缺失问用户、用户不告知则自远端下载安装；新增 `refresh_cache.py` 本地缓存脚本；以远端 URL 为稳定锚点、不写死本地绝对路径。
- `obscura` v1.2.1 (Dev Workflow): Rust 开源无头浏览器技能，网页抓取/截图/PDF/AI 自动化/搜索（含一键 `search.sh`），内置一键安装脚本 `install.sh`，见 [skills/dev-workflow/obscura](skills/dev-workflow/obscura/)。

## Maintenance Contract

Keep `README.md`, this `WIKI.md`, and the relevant `wiki/*.md` page in sync
when repository behavior changes. The root `WIKI.md` should stay an index; do
not move long process documentation back into this file.

Run the documentation freshness guard before committing behavior-changing
changes:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```
