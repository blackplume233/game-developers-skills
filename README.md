# Game Developers Skills

AI Agent 技能私有仓库，兼容 [skills.sh](https://skills.sh/) / `npx skills` 生态。

## 必装技能

首次使用本仓库？建议先安装 **skill-repo-manager**，它是管理本仓库的核心技能——支持搜索、安装、发布技能，并在每次上传时自动执行版本校验和 AI 隐私审查。

```bash
npx skills add blackplume233/game-developers-skills --skill skill-repo-manager -g -y
```

> 本仓库是私有仓库，安装前需要确保当前机器已经具备 GitHub 访问权限。推荐先运行 `gh auth status` 确认已登录，再安装。若 `npx skills add` 因私有仓库、TLS 或默认分支失败，见 [Installation](wiki/Installation.md) 的私有仓库安装排障流程。

`skill-repo-manager` 在仓库中的真实路径是 `skills/skill-management/skill-repo-manager/`，仓库默认分支是 `master`。使用直接下载或自定义安装脚本时需要显式使用该路径和分支。

安装后，你可以直接在 AI Agent 对话中说「上传技能」「搜索技能」「发布到仓库」等，agent 会自动调用此技能完成完整的发布流程（版本检查 → 隐私审计 → Changelog → README/Wiki → 提交 → 推送）。

> **示例**：本仓库中的 [gua（周易揲蓍占卦）](skills/divination/gua/) 技能就是通过 `skill-repo-manager` 完成审查与上传的。

## 项目 Wiki

维护流程、发布规则和引用仓库说明见 [WIKI.md](WIKI.md) 以及 `wiki/` 目录下的页面。仓库行为变更必须在同一提交中同步 `README.md`、`WIKI.md` 和相关 Wiki 页面。

## 技能目录

## 引用仓库

| 仓库 | 路径 | 说明 |
|------|------|------|
| [claude-code-game-studios](https://github.com/donchitos/claude-code-game-studios) | [references/claude-code-game-studios](references/claude-code-game-studios/) | Claude Code 游戏工作室流程技能集合，可通过 `find-skills` 搜索发现 |
| [trellis](https://github.com/mindfold-ai/trellis) | [references/trellis](references/trellis/) | Mindfold Trellis AI 工作流系统，可通过 `find-skills` 搜索发现 |

### Agent Orchestration（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [codex-subagent](skills/agent-orchestration/codex-subagent/) | 1.0.0 | 将子任务委托给 Codex CLI 执行 |
| [auto-goal](skills/agent-orchestration/auto-goal/) | 1.2.0 | 文件驱动的自动 Goal 执行、Markdown 状态表格、用户确认与验证循环 |

### Skill Management（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [find-skills](skills/skill-management/find-skills/) | 1.1.0 | 从本仓库、引用仓库和 skills.sh 生态发现和安装技能 |
| [skill-repo-manager](skills/skill-management/skill-repo-manager/) | 1.2.0 | 管理本仓库：搜索、安装、引用外部技能仓库、README/Wiki 同步、发布（含版本校验+AI 隐私审查） |

### Design（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [shadcn-ui](skills/design/shadcn-ui/) | 1.0.0 | shadcn/ui 组件集成、定制与最佳实践 |
| [ui-ux-pro-max](skills/design/ui-ux-pro-max/) | 1.0.0 | UI/UX 设计系统智能，BM25 搜索引擎 + 13 个技术栈 + 设计数据库 |

### Framework（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [electron](skills/framework/electron/) | 1.0.0 | Electron 桌面应用 CDP 自动化（VS Code, Slack, Discord 等） |
| [tauri-v2](skills/framework/tauri-v2/) | 1.0.1 | Tauri v2 跨平台开发完整指南（IPC、权限、插件、移动端） |

### Dev Workflow（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [git-commit](skills/dev-workflow/git-commit/) | 1.0.0 | Conventional Commits 规范化提交工作流 |
| [guard](skills/dev-workflow/guard/) | 1.0.0 | 高风险操作安全护栏，防止盲目推进 |
| [investigate](skills/dev-workflow/investigate/) | 1.0.0 | 系统性根因调查方法论（假设→验证→根因→修复建议） |
| [project-wiki-maintainer](skills/dev-workflow/project-wiki-maintainer/) | 1.1.0 | 维护项目 Wiki 与 README，并提供文档新鲜度检查 |

### Divination（通用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [gua](skills/divination/gua/) | 1.0.0 | 周易揲蓍占卦推演，以大语言模型直觉替代蓍草随机性 |

### GAS Extension（项目专用）

| 技能 | 版本 | 说明 |
|------|------|------|
| [qa](skills/gas-extension/qa/) | 1.0.0 | Playwright E2E 测试工程师，6 种测试模式 |
| [ship](skills/gas-extension/ship/) | 1.0.0 | 一站式交付流水线：审查→构建→验证→提交→推送 |

## 快速安装

```bash
# 安装单个技能
npx skills add blackplume233/game-developers-skills --skill guard -g -y

# 私有仓库安装前先确认 GitHub CLI 已登录
gh auth status

# 全局安装所有通用技能
npx skills add blackplume233/game-developers-skills \
  --skill codex-subagent --skill auto-goal --skill find-skills --skill skill-repo-manager \
  --skill shadcn-ui --skill ui-ux-pro-max --skill electron --skill tauri-v2 \
  --skill git-commit --skill guard --skill investigate --skill project-wiki-maintainer \
  --skill gua \
  -g -y

# 项目级安装 GAS 扩展技能
cd ~/game-agent-extension
npx skills add blackplume233/game-developers-skills --skill qa --skill ship

# 一键全部安装
npx skills add blackplume233/game-developers-skills --skill '*' -g -y
```

## 版本规范

每个 `SKILL.md` 的 YAML frontmatter 中包含 `version` 字段，遵循语义化版本：

- `major.minor.patch`（如 `1.2.0`）
- 新技能首次发布：`1.0.0`
- 内容修复（typo、措辞）：patch +1
- 功能增强（新章节、新脚本）：minor +1
- 破坏性变更（重命名、删除、不兼容）：major +1

上传时由 `skill-repo-manager` 强制校验版本号只能递增。

## 隐私审查

每次上传前由 AI Agent 执行语义级隐私审查，检查 5 个维度：

1. **CRITICAL** — 密钥凭证（API Key、Token、Secret）
2. **HIGH** — 身份信息（用户名、邮箱）、硬编码路径
3. **MEDIUM** — 业务敏感（内部产品名、未公开 API）
4. **LOW** — 泛化程度（项目特定引用）

详见 [docs/privacy-audit-guide.md](docs/privacy-audit-guide.md)。

## 目录结构

```
.
├── WIKI.md                 # 项目 Wiki 与维护规则
├── wiki/                   # 项目 Wiki 页面
│   ├── Home.md
│   ├── Installation.md
│   ├── Skill-Publishing.md
│   ├── Referenced-Skill-Repositories.md
│   └── Maintenance-Rules.md
├── references/             # 外部技能仓库 git submodule 引用
│   ├── claude-code-game-studios/
│   └── trellis/
└── skills/
    ├── agent-orchestration/    # 通用 - Agent 编排
    │   ├── codex-subagent/
    │   └── auto-goal/
    ├── design/                 # 通用 - UI/UX 设计
    │   ├── shadcn-ui/
    │   └── ui-ux-pro-max/
    │       ├── SKILL.md
    │       ├── scripts/        # BM25 搜索引擎
    │       └── data/           # 11 CSV + 13 技术栈
    ├── framework/              # 通用 - 框架开发
    │   ├── electron/
    │   └── tauri-v2/
    │       ├── SKILL.md
    │       └── references/     # 5 份深度参考文档
    ├── dev-workflow/           # 通用 - 开发工作流
    │   ├── git-commit/
    │   ├── guard/
    │   ├── investigate/
    │   └── project-wiki-maintainer/
    │       ├── SKILL.md
    │       ├── agents/
    │       └── scripts/        # README/Wiki 新鲜度检查
    ├── skill-management/       # 通用 - 技能管理
    │   ├── find-skills/
    │   │   ├── SKILL.md
    │   │   └── scripts/        # 本地与引用仓库技能搜索
    │   └── skill-repo-manager/
    │       ├── SKILL.md
    │       └── scripts/        # 引用仓库子模块、发布辅助
    ├── divination/             # 通用 - 占卜推演
    │   └── gua/
    │       ├── SKILL.md
    │       └── reference.md    # 六十四卦速查表
    └── gas-extension/          # GAS 扩展专用
        ├── qa/
        │   ├── SKILL.md
        │   ├── pitfalls.md
        │   ├── commands/
        │   └── scenarios/
        └── ship/
            ├── SKILL.md
            └── commands/
```
