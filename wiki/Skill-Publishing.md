# Skill Publishing

Use `skill-repo-manager` for publishing repository changes. The manager defaults
to `blackplume233/game-developers-skills` when no other repository is named. Do
not skip or reorder the gates below.

## Required Gates

1. Version check for changed skills
2. AI privacy audit over every changed skill file
3. Changelog update
4. README and Wiki update
5. Focused git commit
6. Push to the repository remote
7. Local skill update or verification when the changed skill is installed locally

## Version Check

Every `SKILL.md` must include a `version` field in YAML frontmatter.

- New skill: start at `1.0.0`
- Content fix: increment patch
- New section or script: increment minor
- Rename, removal, or incompatible behavior: increment major

For existing skills, compare the working tree version with the repository
version:

```bash
git show HEAD:skills/<category>/<skill-name>/SKILL.md
```

Block publishing when the new version is missing, unchanged, or lower.

## Privacy Audit

The AI agent must read every file in the changed skill directory and apply
semantic review. Do not rely only on regex scripts.

Review these dimensions:

- CRITICAL: API keys, tokens, passwords, private keys, secrets
- HIGH: real usernames, emails, phone numbers, hardcoded user paths, internal
  addresses
- MEDIUM: unpublished APIs, proprietary details, sensitive business logic
- LOW: project-specific references in skills claiming to be universal

If `.privacy-rules.yaml` exists, read it before making the final audit decision.

## Current Skill Notes

- `auto-goal` v1.3.0 stores program-controlled goal state in top-level YAML frontmatter, keeps helper scripts for state reads and updates, remains compatible with older state tables, requires user confirmation after drafting goal files, and applies grill-me style clarification for ambiguous goals.
- `qa` v2.0.0 is a generic Dev Workflow skill. It should guide agents to operate the real product entry, collect evidence incrementally, judge behavior like a responsible engineer, and save stable exploratory or regression paths as project test cases.

## Changelog

Update `CHANGELOG.md` under the current release/date section:

- New skill: `Added <name> v<version> (<category>)`
- Updated skill: `Updated <name> v<old> -> v<new>`
- Removed skill: `Removed <name>`

## Documentation

Update these together when the change affects usage, workflow, install commands,
skill availability, release process, or layout:

- `README.md`
- `WIKI.md`
- The relevant page under `wiki/`

Run:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```

## Commit And Push

Stage only the files related to the change:

```bash
git add skills/<category>/<skill-name>/ CHANGELOG.md README.md WIKI.md wiki/
```

Use focused commit messages:

- New: `feat(skills): add <name> v<version>`
- Update: `fix(skills): update <name> v<version>`
- Breaking: `feat(skills)!: <description>`

Push the current branch:

```bash
git push origin <current-branch>
```
