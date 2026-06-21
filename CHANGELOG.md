# Changelog

All notable changes to this skill repository will be documented in this file.

## [1.5.0] - 2026-06-21

### Added

- `auto-goal` v1.0.0: added a file-backed automatic Goal execution skill for Codex, Claude, and other agents, with repository-baseline capture, live editable goal files, HTN-style recursive decomposition, subagent guidance, and self-correcting loop evidence.
- `skill-repo-manager` v1.1.0: add an external skill repository reference operation that creates `references/<repo>` git submodules and lists discovered `SKILL.md` files.
- `find-skills` v1.1.0: add a local search helper that scans this repository plus referenced skill repositories under `references/`.
- Reference `trellis` (`donchitos/claude-code-game-studios`) as `references/trellis` for game studio workflow skills.

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
