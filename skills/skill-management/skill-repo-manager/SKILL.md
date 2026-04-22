---
name: skill-repo-manager
version: 1.0.0
description: >-
  Manage a private Skill repository: search (local repo + skills.sh),
  install (to any agent directory), and publish (version check + AI privacy
  audit + git push). Triggers on: "manage skills", "upload skill",
  "publish skill", "skill search", "skill repo", "skill upload",
  "技能仓库", "上传技能", "发布技能", "技能搜索".
---

# Skill Repo Manager

Manages your private Skill repository. Activates when you need to search,
install, or publish Skills.

## Prerequisites

- Repository cloned locally (path referred to as `$REPO`)
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
# Install specific skill globally
npx skills add <owner>/<repo> --skill <name> -g

# Install to current project
npx skills add <owner>/<repo> --skill <name>

# Install all skills
npx skills add <owner>/<repo> --skill '*' -g -y
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

### Step 4: Git Commit

1. Stage only the target skill files + CHANGELOG.md:
   ```bash
   git add skills/<category>/<skill-name>/ CHANGELOG.md
   ```
2. Commit message format:
   - New: `feat(skills): add <name> v<version>`
   - Update: `fix(skills): update <name> v<version>`
   - Breaking: `feat(skills)!: <description>`
3. Execute `git commit`

### Step 5: Push

1. `git push origin main`
2. Remind user to run `npx skills update` on other machines

## Important Rules

- NEVER skip the version check or privacy audit when publishing
- NEVER push code that has unresolved CRITICAL privacy issues
- NEVER decrement a version number
- When in doubt about privacy, flag as HIGH and ask the user
