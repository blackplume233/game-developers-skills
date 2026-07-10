---
name: skill-repo-manager
version: 1.4.0
description: >-
  Manage a private Skill repository: search (local repo + skills.sh),
  install (to any agent directory), reference external skill repositories as
  git submodules, keep README and Wiki synchronized for every repository
  change, publish (version check + AI privacy audit + git push), and maintain
  ordinary personal-repository listings on skills.sh. Triggers
  on: "manage skills", "upload skill", "publish skill", "skill search",
  "skill repo", "skill upload", "reference skill repo", "update wiki",
  "技能仓库", "上传技能", "发布技能", "技能搜索", "引用技能仓库",
  "skills.sh 收录", "skills.sh.json", "技能页面分组".
---

# Skill Repo Manager

Manages your private Skill repository. Activates when you need to search,
install, reference external skill repositories, update repository docs, or
publish Skills.

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
- Git push access configured

## Operation 1: Search

### 1.1 Local Repository Search

1. Recursively scan `$REPO/skills/` for all `SKILL.md` files
2. Parse YAML frontmatter (`name`, `version`, `description`) from each
3. Match the user's keyword against name and description
4. Output in this format:

```
[category] name vX.Y.Z — description
  path: skills/<category>/<skill-name>/
```

### 1.2 skills.sh Marketplace Search

```bash
npx skills find "<keyword>"
```

Present results. If the user wants to install, proceed to Operation 2.

### 1.3 List Installed Skills

```bash
npx skills list          # current project
npx skills ls -g         # global (user-level)
npx skills ls -a cursor  # filter by agent
```

## Operation 2: Install

### 2.1 From Private Repository

```bash
# Install specific skill globally from the default repository
npx skills add blackplume233/game-developers-skills --skill <name> -g

# Install to current project from the default repository
npx skills add blackplume233/game-developers-skills --skill <name>

# Install all skills from the default repository
npx skills add blackplume233/game-developers-skills --skill '*' -g -y
```

### 2.2 From skills.sh Marketplace

```bash
npx skills add <owner>/<repo> --skill <name> -g
```

### 2.3 Post-install Verification

After installing, verify that SKILL.md exists in the target directory:
- Cursor: `~/.cursor/skills/<name>/SKILL.md`
- Claude: `~/.claude/skills/<name>/SKILL.md`
- Agents: `~/.agents/skills/<name>/SKILL.md`

## Operation 3: Publish

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

## Operation 4: Reference External Skill Repository

Use this when the user gives a Git URL or local repository path and asks to
make its skills discoverable from this repository without copying the source
files.

### 4.1 Add as a git submodule

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

### 4.2 Verify discovery through find-skills

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

### 4.3 Commit scope

When publishing a new reference, stage only the submodule metadata and any
skill documentation updates:

```bash
git add .gitmodules references/<reference-name> skills/skill-management/skill-repo-manager/ skills/skill-management/find-skills/ README.md WIKI.md CHANGELOG.md
```

Do not vendor-copy the referenced repository into `skills/`; keep it as a
submodule so ownership and upstream history remain intact.

## Operation 5: skills.sh 普通仓库收录与页面定制

用于个人或社区仓库的普通收录。不要把它描述成 `Official` 申请：`Official`
面向技术产品的官方组织，`skills.sh.json` 只控制已收录仓库页面的分组展示。

### 5.1 判断收录状态

访问 `https://www.skills.sh/<owner>/<repo>`。页面存在即表示仓库已被普通收录；
技能数量不完整通常表示遥测尚未见到所有技能或页面缓存尚未刷新。

### 5.2 生成并校验仓库页面配置

在仓库根目录执行：

```bash
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --write
python skills/skill-management/skill-repo-manager/scripts/sync_skills_sh.py --check
```

脚本扫描 `skills/<category>/<skill>/SKILL.md`，读取 frontmatter 的 `name`，
按目录类别生成根目录 `skills.sh.json`，并检查重复技能名和配置漂移。
生成后仍需人工确认分组标题、描述和技能 slug 是否符合页面预期；页面已经生成过
URL 时，优先采用 URL 中的 slug。

### 5.3 发布与触发发现

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

### 5.4 配置边界

- `skills.sh.json` 必须位于 GitHub 仓库根目录且为合法 JSON。
- `groupings` 至少包含一个有效分组；未列出的技能进入 `Other skills`。
- 配置只影响 skills.sh 页面展示，不改变 CLI 安装行为或 `SKILL.md` 内容。
- 普通收录与排行榜由 CLI 匿名安装遥测驱动，无需提交 Official 申请。
- 不承诺缓存刷新时间，也不要通过重复安装伪造热度。

## Important Rules

- NEVER skip the version check or privacy audit when publishing
- NEVER push code that has unresolved CRITICAL privacy issues
- NEVER decrement a version number
- NEVER commit repository changes without updating or validating both README.md
  and WIKI.md
- NEVER copy a referenced external repository into this repo when the user
  asked for a reference/submodule
- NEVER claim that `skills.sh.json` grants Official status; it only customizes an ordinary repo page
- When in doubt about privacy, flag as HIGH and ask the user
