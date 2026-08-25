# Changelog

All notable changes to this skill repository will be documented in this file.

## [1.12.0] - 2026-08-25

### Changed

- Updated `qa` v2.0.0 -> v2.1.0: 黑盒测试执行的每一步操作必须是真实用户能自行复现的动作，不能用内部旁路（改库、内部调试接口、跳过鉴权）代替；正式操作真实入口前必须先写好用户可复现的测试方案（步骤 + 预期结果），`explore` 模式至少先写最小 charter；强调每一个执行的操作都要即时记录，不能遗漏。

## [1.11.0] - 2026-08-23

### Fixed

- `obscura` v1.2.1: `search.sh` now filters out DuckDuckGo/Bing sponsored ad links (y.js / ad_domain / "more info") so search results contain only organic entries.

### Changed

- Updated `obscura` v1.1.0 -> v1.2.0: add a `search.sh` one-click search script that searches DuckDuckGo/Bing, extracts structured results (`title\tURL`), decodes real URLs, auto-installs obscura, and URL-encodes Chinese keywords for Agent use.
- Updated `obscura` v1.0.0 -> v1.1.0: add a Search section (DuckDuckGo lite / Bing / Google) with fetch, links, eval, parallel scrape, and URL-decoding tips for extracting search-engine results.
- Updated `skill-repo-manager` v1.4.0 -> v1.5.0: 升级为路由式主文案（顶部 Dispatch 路由表分诊 Finder/Publisher 两线）；新增 Finder 主动按需检索——本地缓存优先、缓存缺失时问用户、用户不告知则自远端下载安装；新增 `refresh_cache.py` 本地缓存脚本；明确本地仓库路径跨设备可变，改以远端 URL 为稳定锚点，不写死任何本地绝对路径。
- Updated `skill-repo-manager` v1.5.0 -> v1.5.1: Finder 自远端下载改为优先直接 `npx skills add <owner>/<repo> --skill <name> -g`, 仅当其失败时才回退手动 `git clone` 复制。
- Updated `skill-repo-manager` v1.5.1 -> v1.5.2: 查询阶段补 fall back——缓存未命中时先本地仓库扫描, 再 `npx skills find <keyword>` 搜索确定技能名后安装。

### Added

- **Dev Workflow** (1 skill):
  - `obscura` v1.0.0 — Rust 开源无头浏览器技能，用于网页抓取、内容提取、截图、PDF 导出和 AI Agent 自动化，支持 V8 真实 JS 渲染与 CDP，兼容 Puppeteer/Playwright，内置一键安装脚本 `install.sh`（含 stealth/no-render 变体）

### Changed

- README: 新增 Dev Workflow 分类下的 `obscura` 技能与安装命令

## [1.10.0] - 2026-08-18

### Added

- Added `game-deconstruction` v1.0.0 (`game-analysis`): a P0–P8, tool-first white-box workflow for authorized game assets, executable mechanism explanations, WebBook delivery, and an Agent-ready knowledge base with CLI, HTTP, OpenAPI, and MCP access.
- Added the Game Analysis Wiki page and installation guidance.

## [1.9.0] - 2026-07-10

### Added

- 根目录新增 `skills.sh.json`，按仓库类别组织全部技能的 skills.sh 页面展示。
- `skill-repo-manager` 新增 `sync_skills_sh.py`，用于从本地技能清单生成和校验页面配置。
- 新增 skills.sh 普通仓库收录、遥测触发、缓存复查与故障排查文档。

### Changed

- Updated `skill-repo-manager` v1.3.0 -> v1.4.0: 支持 skills.sh 普通个人仓库收录与页面维护，并明确其与 Official 的边界。

## [1.8.0] - 2026-07-02

### Changed

- Updated `qa` v1.0.0 -> v2.0.0: move from `gas-extension` to `dev-workflow`, remove project-specific content, and refocus the skill on generic real-operation QA, evidence-based engineering judgment, and automatic test-case capture.

## [1.7.0] - 2026-06-30

### Changed

- Updated `skill-repo-manager` v1.2.0 -> v1.3.0: default repository operations to `blackplume233/game-developers-skills` when no other skill repository is specified.

## [1.6.1] - 2026-06-26

### Changed

- Updated `auto-goal` v1.2.0 -> v1.3.0: move program-controlled goal state fields to top-level YAML frontmatter while keeping compatibility with older Markdown state tables.

## [1.6.0] - 2026-06-23

### Added

- `wiki/`: add a multi-page in-repository Wiki with Home, Installation, Skill Publishing, Referenced Skill Repositories, and Maintenance Rules pages.

### Changed

- Updated `project-wiki-maintainer` v1.0.0 -> v1.1.0: support `wiki/` as a first-class documentation directory in the freshness guard and Wiki maintenance guidance.
- `README.md` and `WIKI.md`: document the multi-page Wiki structure and private repository installation troubleshooting.

## [1.5.0] - 2026-06-21

### Added

- `auto-goal` v1.0.0: added a file-backed automatic Goal execution skill for Codex, Claude, and other agents, with repository-baseline capture, live editable goal files, HTN-style recursive decomposition, subagent guidance, and self-correcting loop evidence.
- `skill-repo-manager` v1.1.0: add an external skill repository reference operation that creates `references/<repo>` git submodules and lists discovered `SKILL.md` files.
- `find-skills` v1.1.0: add a local search helper that scans this repository plus referenced skill repositories under `references/`.
- Reference `donchitos/claude-code-game-studios` as `references/claude-code-game-studios` for game studio workflow skills.
- Reference `mindfold-ai/trellis` as `references/trellis` for Trellis AI workflow skills.
- `project-wiki-maintainer` v1.0.0: add a generic workflow for maintaining project Wiki and README together, with a `wiki_guard.py` freshness gate.
- `WIKI.md`: add repository maintenance rules, publishing gates, referenced repository notes, and local skill update guidance.

### Changed

- Updated `auto-goal` v1.0.0 -> v1.1.0: switch the skill, bundled templates, UI metadata, and validator output to Chinese; add `artifact_language` as a required goal-state field so durable documents and native Goal objectives follow repository language preferences.
- Updated `skill-repo-manager` v1.1.0 -> v1.2.0: require README and Wiki updates for every repository change and reference `project-wiki-maintainer` as the documentation gate.
- Updated `auto-goal` v1.1.0 -> v1.2.0: use Markdown state tables with helper scripts, require user confirmation after goal draft generation, apply grill-me style clarification for ambiguous goals, and prefer workspace artifact roots under `goal/<date-slug>/`.

## [1.4.0] - 2026-04-30

### Removed

- `paseo` v1.0.0
- `paseo-chat` v1.0.0
- `paseo-committee` v1.0.0
- `paseo-handoff` v1.0.0
- `paseo-loop` v1.0.0
- `paseo-orchestrator` v1.0.0

## [1.3.0] - 2026-04-29

### Added

- **Divination** (1 skill):
  - `gua` v1.0.0 — 周易揲蓍占卦推演，以大语言模型直觉替代蓍草随机性

### Changed

- README: 新增「必装技能」章节，将 `skill-repo-manager` 作为使用本仓库的推荐首装技能
- README: 新增 Divination 分类

## [1.2.0] - 2026-04-28

### Added

- **Skill Management** (1 skill):
  - `create-watch-skill` v1.0.0 - human-in-the-loop watch skill creation workflow

## [1.1.0] - 2026-04-22

### Added

- **Design** (2 skills):
  - `shadcn-ui` v1.0.0 — shadcn/ui component integration and best practices
  - `ui-ux-pro-max` v1.0.0 — UI/UX design intelligence with BM25 search engine, 11 data CSVs, 13 stack guides, 3 Python scripts

- **Framework** (2 skills):
  - `electron` v1.0.0 — Electron desktop app automation via Chrome DevTools Protocol
  - `tauri-v2` v1.0.1 — Tauri v2 cross-platform development (IPC, permissions, plugins, mobile) with 5 reference documents

- **Dev Workflow** (3 skills):
  - `git-commit` v1.0.0 — Conventional Commits workflow (generalized from AgentCraft)
  - `guard` v1.0.0 — High-risk session safety guardrail (generalized from actant-next)
  - `investigate` v1.0.0 — Systematic root cause investigation methodology (generalized from actant-next)

- Updated README.md with new skill categories and installation commands

## [1.0.0] - 2026-04-22

### Added

- **Agent Orchestration** (7 skills):
  - `paseo` v1.0.0 — Paseo CLI reference
  - `paseo-chat` v1.0.0 — Chat room coordination
  - `paseo-committee` v1.0.0 — Dual-agent committee planning
  - `paseo-handoff` v1.0.0 — Task handoff between agents
  - `paseo-loop` v1.0.0 — Iterative worker/verifier loops
  - `paseo-orchestrator` v1.0.0 — Team orchestration via chat
  - `codex-subagent` v1.0.0 — Codex CLI sub-agent delegation

- **Skill Management** (2 skills):
  - `find-skills` v1.0.0 — Discover and install skills from skills.sh
  - `skill-repo-manager` v1.0.0 — Repository self-management (search/install/publish with version check + AI privacy audit)

- **GAS Extension** (2 skills):
  - `qa` v1.0.0 — Playwright E2E testing with 7 scenarios
  - `ship` v1.0.0 — Ship pipeline (review → build → verify → commit → push)

- Repository infrastructure:
  - `.privacy-rules.yaml` — Privacy audit reference rules
  - `docs/privacy-audit-guide.md` — Audit process documentation
  - `README.md` — Skill index and usage guide
