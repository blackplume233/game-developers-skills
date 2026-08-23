---
name: skill-repo-manager
version: 1.5.2
description: >-
  路由式技能仓库管理技能。主文案即路由表, 分诊两类场景: ①能力缺口时主动按需
  检索技能——本地缓存优先、缓存缺失时问用户、用户不告知则自远端下载安装
  (Finder, §A); ②技能仓库的搜索/安装/引用外部仓库/发布/README-Wiki 同步/
  skills.sh 收录 (Publisher, §B)。Trigs on: "技能仓库", "上传技能", "发布技能",
  "技能搜索", "引用技能仓库", "update wiki", "skills.sh 收录", "skills.sh.json",
  "技能页面分组", 以及能力缺口类请求——"我需要 X 技能", "帮我找个做 X 的技能",
  "你会不会做 X", "给我装一个 X 技能", "缓存技能", "下载技能", "skill cache",
  "skill repo".
---

# Skill Repo Manager（路由式）

本技能是**路由式主文案**：正文以「路由表」开头。收到请求后**先查路由表分诊**，
再进入对应章节执行，不要平铺全部逻辑。

## 🧭 路由表（Dispatch）

按用户意图路由到对应章节：

| 用户意图 | 路由 | 章节 |
|---------|------|------|
| 需要某能力 / 找技能 / 装技能 / "你会不会做 X" | → Finder | §A |
| 缓存刷新 / 自远端下载 / 换设备重建缓存 | → Finder | §A |
| 发布技能 / 版本检查 / 隐私审计 / push | → Publisher | §B |
| 引用外部技能仓库 (submodule) | → Publisher | §B |
| 仓库文档同步 (README/Wiki) / skills.sh 收录 | → Publisher | §B |

## Default Repository

Unless the user provides another repository, treat this repository as the
default private skill repository:

```text
blackplume233/game-developers-skills
```

Use this default for repository search, install, reference, publish, update, and
GitHub access checks. If a local clone is needed and the current working
directory is not the skill repository, locate an existing clone first; otherwise
clone `https://github.com/blackplume233/game-developers-skills.git` into a
temporary or user-selected workspace before editing.

## Prerequisites

- Repository cloned locally (path referred to as `$REPO`); by default this is
  `blackplume233/game-developers-skills`
- Node.js installed (for `npx skills`)
- Git push access configured (only needed for §B Publisher)
- **本地缓存**: `~/.agents/skills/.skill-repo-cache.json` — Finder 按需检索的
  本地索引, 各设备自维护。**本地仓库路径跨设备可变, 远端 URL 才是稳定锚点**;
  本技能不写死任何本地绝对路径。

---

# §A Finder：主动按需检索技能（使用者向）

## A1 何时触发

当用户的任务需要某项能力、而当前**未安装对应技能**时, 主动走本节。典型信号:
用户明确要某技能、或任务域明显有现成技能（做 PPT → `pptx`, 抓网页 → `obscura`,
做游戏 → `game-deconstruction` 等）。

## A2 本地缓存优先（优先级 1）

1. 读取缓存 `~/.agents/skills/.skill-repo-cache.json`
2. 在 `cache.skills` 中按 `name` 和 `description` 匹配用户需求
3. 命中且 `installed: true` → 直接告知用户已装, 结束
4. 命中但 `installed: false` → 用 §A5 的安装命令从 `cache.local_path` 安装,
   装完把该项 `installed` 置为 `true` 并写回缓存

缓存不存在或**未命中** → 进入查询 fall back：见 §A5 先做本地仓库扫描,
仍未命中则 `npx skills find <keyword>` 搜索确定技能名, 找到后按 §A3/§A5 安装;
都找不到 → 走 §A4（问用户）或回退 §A3（自远端下载）。

## A3 自远端下载（优先级 2，用户不告知时）

当 `cache.local_path` 为空、缓存缺失、且用户**没有提供本地路径**时, 仍可自行
从远端完成下载与安装, 不阻塞。**优先直接用 `npx skills add` 从远端安装**, 无需
自建 clone/复制逻辑:

1. 用缓存清单（见 §A6）或 `npx skills find` 确定目标技能名 `<name>`
2. 直接下载并安装到当前设备全局技能目录:
   ```bash
   npx skills add blackplume233/game-developers-skills --skill <name> -g -y
   ```
   该命令由 Skills CLI 从远端仓库拉取并安装到 `~/.agents/skills/<name>/`,
   不经由手动 clone/复制
3. 仅当 `npx skills add` 因私有仓库/TLS/默认分支失败时, 才回退手动方式:
   `git clone --depth 1 <url> <tmp>` 后复制技能目录到 `~/.agents/skills/<name>/`
4. 装完更新缓存 (`installed: true`, `local_path` 记录仓库路径)

## A4 问用户兜底（优先级 3）

当本地缓存、远端自下载都拿不到目标技能时, **明确问用户**, 不要自行猜测:
- 请用户提供该技能（本地路径 / 远端 URL / 源码目录）;
- 或确认"当前没有现成技能, 先用通用能力直接完成"。

用户不告知也不影响继续: 始终可回退到 §A3 的自下载尝试。

## A5 检索与安装手段（Finder 通用）

### 本地仓库检索

1. 递归扫描 `$REPO/skills/` 所有 `SKILL.md`, 解析 frontmatter (`name`,
   `version`, `description`)
2. 按关键词匹配 name 和 description
3. 输出格式:

```
[category] name vX.Y.Z — description
  path: skills/<category>/<skill-name>/
```

### 查询 fall back：`npx skills find`（确定技能名）

当本地缓存未命中、本地仓库扫描也找不到时, 用 `npx skills find` 搜索确定
要装哪个技能, 再安装:

```bash
npx skills find "<keyword>"
```

`npx skills find` 是本技能**确定目标技能名 `<name>` 的查询兜底**: 它同时覆盖
本地仓库与 skills.sh 市场。找到后, 用 §A3 的 `npx skills add` 下载安装。

### 从私有仓库安装

```bash
npx skills add blackplume233/game-developers-skills --skill <name> -g
npx skills add blackplume233/game-developers-skills --skill '*' -g -y   # 全量
```

### 从 skills.sh 市场安装

```bash
npx skills add <owner>/<repo> --skill <name> -g
```

### 安装后验证

确认目标目录存在 `SKILL.md`:
- Cursor: `~/.cursor/skills/<name>/SKILL.md`
- Claude: `~/.claude/skills/<name>/SKILL.md`
- Agents: `~/.agents/skills/<name>/SKILL.md`

## A6 缓存维护

- **刷新缓存**: 在仓库根运行
  ```bash
  python skills/skill-management/skill-repo-manager/scripts/refresh_cache.py
  ```
  可选 `--repo-root <path>` / `--repo-url <url>` / `--cache-out <path>`。
  脚本重扫 `skills/**/SKILL.md` 生成清单, 保留历史 `installed` 状态。
- **换设备/首用**: 缓存不存在时, 先让用户提供仓库本地路径或远端 URL 生成一次,
  之后该设备自维护; 用户不提供则回退 §A3 远端自下载。
- **手动修正**: 缓存是普通 JSON, 可直接编辑。

---

# §B Publisher：技能仓库维护（作者向）

## Operation 1: Publish

The most critical operation. Follow these five steps strictly in order.
Do NOT skip or reorder any step.

### Step 1: Version Check (mandatory, cannot skip)

1. Read the `version` field from the SKILL.md frontmatter of the skill
   being published
2. Read the current version in the repository via:
   `git show HEAD:skills/<path>/SKILL.md`
   Parse its `version` field from the frontmatter
3. Compare versions:

| Situation | Rule |
|-----------|------|
| New skill (not in repo) | `version` MUST be `1.0.0` |
| Existing skill | New version MUST be strictly greater than repo version |
| Version unchanged or decreased | **BLOCK upload** — ask user to increment |
| `version` field missing | **BLOCK upload** — ask user to add it |

4. Version increment guidelines to suggest to the user:
   - Content fix (typo, wording) → patch: `1.0.0` → `1.0.1`
   - Feature addition (new section, new script) → minor: `1.0.1` → `1.1.0`
   - Breaking change (rename, remove, incompatible) → major: `1.1.0` → `2.0.0`

5. Only proceed to Step 2 after version check passes.

### Step 2: Privacy Audit (mandatory, cannot skip)

This audit is performed by you (the AI agent) through direct content
observation. Do NOT delegate to a script. Read every file yourself and
apply semantic judgment.

#### 2a. Read all files

Read every file in the skill directory: SKILL.md, scripts/, references/,
commands/, scenarios/, and any other files. Do not skip any.

#### 2b. Review each file against 5 dimensions

For each file, evaluate these dimensions:

**CRITICAL — Secrets & Credentials**
- API keys, tokens, secrets, passwords, private keys
- Judgment: distinguish real values (high entropy, known formats like
  `sk-`, `ghp_`, `AKIA`, assignment context) from placeholders and
  documentation examples (`sk-example`, `your-api-key-here`)

**HIGH — Identity Information**
- Real usernames, email addresses, phone numbers, real names
- Judgment: author attribution in frontmatter is acceptable; user data
  embedded in instructions is not

**HIGH — Hardcoded Paths & Environments**
- Absolute paths: `C:\Users\<name>\...`, `/home/<name>/...`
- Internal URLs: localhost, 127.0.0.1, 192.168.x, 10.x, *.internal
- Judgment: convention paths like `~/.cursor/skills/` are acceptable;
  paths containing specific usernames are not

**MEDIUM — Business Sensitive**
- Internal product names, unpublished APIs, architecture details,
  proprietary business logic
- Judgment: would this information give competitors an advantage or
  violate NDA if published publicly?

**LOW — Generalization**
- Project-specific references in skills claiming to be universal
- Team-internal jargon
- Judgment: would an outsider be confused by these references?

#### 2c. Extra observations (beyond regex capability)

Also watch for:
- Base64-encoded sensitive data (long random-looking strings)
- Environment variable references with hardcoded fallback values
- Residual information in comments or TODOs (temporary credentials)
- Composite inference risk: individually harmless fields (username,
  city, company) that together uniquely identify a person

#### 2d. Read .privacy-rules.yaml

If `$REPO/.privacy-rules.yaml` exists, read it for additional custom
rules, known-safe patterns, and excluded paths.

#### 2e. Generate audit report

Output in this exact format:

```
=== Privacy Audit Report ===
Skill: <skill-name>
Version: <version>
Files reviewed: <N>
Audit time: <timestamp>

[CRITICAL] <count>
  - <file>:<line> <description>
    → Fix: <specific remediation>

[HIGH] <count>
  - <file>:<line> <description>
    → Fix: <specific remediation>

[MEDIUM] <count>
  - <file>:<line> <description>
    → Suggestion: <recommendation>

[LOW] <count>
  - <file>:<line> <description>
    → Note: <recommendation>

Verdict: PASS | WARNING | BLOCK
```

#### 2f. Decision

- **CRITICAL > 0** → **BLOCK upload**. List all issues with fixes.
  You MUST NOT execute `git push` until the user resolves all CRITICAL
  issues. After fixes, re-audit from Step 2a.
- **HIGH > 0** → **Pause**. Explain each risk to the user. Ask whether
  to fix or explicitly waive each item. Only proceed after user confirms.
- **MEDIUM / LOW** → Display suggestions. Do not block.

### Step 3: Changelog (repository-level)

1. Read current `$REPO/CHANGELOG.md`
2. Add an entry under today's date:
   - New skill: `Added <name> v<version> (<category>)`
   - Updated skill: `Updated <name> v<old> → v<new>`
   - Removed skill: `Removed <name>`

### Step 3.5: README and Wiki (mandatory for every repository change)

Every repository change must update or explicitly validate both README and
Wiki. Use `project-wiki-maintainer` for this gate.

1. Update `README.md` with user-facing index, install, usage, or layout changes
2. Update `WIKI.md` with durable workflow/process/maintenance changes
3. Run:
   ```bash
   python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
   ```
4. If the guard fails, update the missing document before committing

### Step 4: Git Commit

1. Stage only the target skill files + CHANGELOG.md + README.md + WIKI.md:
   ```bash
   git add skills/<category>/<skill-name>/ CHANGELOG.md README.md WIKI.md
   ```
2. Commit message format:
   - New: `feat(skills): add <name> v<version>`
   - Update: `fix(skills): update <name> v<version>`
   - Breaking: `feat(skills)!: <description>`
3. Execute `git commit`

### Step 5: Push

1. `git push origin <current-branch>`
2. Remind user to run `npx skills update` on other machines

## Operation 2: Reference External Skill Repository

Use this when the user gives a Git URL or local repository path and asks to
make its skills discoverable from this repository without copying the source
files.

### 2.1 Add as a git submodule

Run the helper from the target skill repository root:

```bash
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <git-url-or-local-path>
```

Optional arguments:

```bash
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <repo> --name <reference-name>
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <repo> --branch <branch-name>
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <repo> --repo-root <path-to-skill-repo>
```

The script:

1. Resolves the target skill repository root
2. Creates `references/` if missing
3. Runs `git submodule add <repo> references/<reference-name>`
4. Initializes the submodule recursively
5. Lists discovered `SKILL.md` files inside the referenced repository

For local repository paths, the script uses Git's per-command
`protocol.file.allow=always` setting so local-path submodules work on modern
Git installations.

### 2.2 Verify discovery through find-skills

After adding the reference, run:

```bash
python skills/skill-management/find-skills/scripts/search_skills.py <keyword>
```

The search helper scans:

- `skills/**/SKILL.md` in this repository
- `references/*/**/SKILL.md` from referenced repositories
- `skills/*/*/references/*/**/SKILL.md` for skill-local references

If the expected skill is not listed, inspect whether the referenced repository
contains valid `SKILL.md` frontmatter with at least `name`, `version`, and
`description`.

### 2.3 Commit scope

When publishing a new reference, stage only the submodule metadata and any
skill documentation updates:

```bash
git add .gitmodules references/<reference-name> skills/skill-management/skill-repo-manager/ skills/skill-management/find-skills/ README.md WIKI.md CHANGELOG.md
```

Do not vendor-copy the referenced repository into `skills/`; keep it as a
submodule so ownership and upstream history remain intact.

## Operation 3: skills.sh 普通仓库收录与页面定制

用于个人或社区仓库的普通收录。不要把它描述成 `Official` 申请：`Official`
面向技术产品的官方组织，`skills.sh.json` 只控制已收录仓库页面的分组展示。

### 3.1 判断收录状态

访问 `https://www.skills.sh/<owner>/<repo>`。页面存在即表示仓库已被普通收录；
技能数量不完整通常表示遥测尚未见到所有技能或页面缓存尚未刷新。

### 3.2 生成并校验仓库页面配置

在仓库根目录执行：

```bash
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --write
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --check
```

脚本扫描 `skills/<category>/<skill>/SKILL.md`，读取 frontmatter 的 `name`，
按目录类别生成根目录 `skills.sh.json`，并检查重复技能名和配置漂移。
生成后仍需人工确认分组标题、描述和技能 slug 是否符合页面预期；页面已经生成过
URL 时，优先采用 URL 中的 slug。

### 3.3 发布与触发发现

将 `skills.sh.json` 与 README、Wiki、CHANGELOG 一起提交并推送。推送成功后运行：

```bash
npx skills add <owner>/<repo> --skill '*' -g -y
```

该安装会通过 Skills CLI 的匿名遥测让 skills.sh 再次看到仓库。然后验证：

1. CLI 输出能发现并安装预期技能；
2. 目标安装目录存在各技能的 `SKILL.md`；
3. 仓库页面最终显示正确的技能数量与分组。

skills.sh 页面有缓存，不能把“推送后立即未更新”判断为失败。记录触发时间，稍后
复查；如果持续不更新，再核对公开仓库、默认分支、合法 `SKILL.md`、实际安装输出
以及 `skills.sh.json` 是否有效。

### 3.4 配置边界

- `skills.sh.json` 必须位于 GitHub 仓库根目录且为合法 JSON。
- `groupings` 至少包含一个有效分组；未列出的技能进入 `Other skills`。
- 配置只影响 skills.sh 页面展示，不改变 CLI 安装行为或 `SKILL.md` 内容。
- 普通收录与排行榜由 CLI 匿名安装遥测驱动，无需提交 Official 申请。
- 不承诺缓存刷新时间，也不要通过重复安装伪造热度。

---

## Important Rules

- NEVER skip the version check or privacy audit when publishing
- NEVER push code that has unresolved CRITICAL privacy issues
- NEVER decrement a version number
- NEVER commit repository changes without updating or validating both README.md
  and WIKI.md
- NEVER copy a referenced external repository into this repo when the user
  asked for a reference/submodule
- NEVER claim that `skills.sh.json` grants Official status; it only customizes an ordinary repo page
- **Finder 永不写死本地绝对路径**: 本地路径跨设备可变, 一律以远端 URL 为锚点,
  本地只通过缓存/探测/用户提供定位
- **缺失即问用户**: 缓存与远端都找不到时, 明确询问用户, 不要自行猜测安装
- When in doubt about privacy, flag as HIGH and ask the user
