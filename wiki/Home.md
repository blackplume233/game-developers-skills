# Game Developers Skills Wiki Home

This Wiki is the durable operating manual for `blackplume233/game-developers-skills`.
The README is the first-time entry point; these pages hold the longer workflows,
maintenance rules, and troubleshooting notes.

## Pages

| Page | Use it for |
|------|------------|
| [Installation](Installation.md) | Installing skills from this private repository and fixing auth or clone failures |
| [Skill Publishing](Skill-Publishing.md) | Publishing new or updated skills through the required gates |
| [Referenced Skill Repositories](Referenced-Skill-Repositories.md) | Managing external repositories under `references/` |
| [Maintenance Rules](Maintenance-Rules.md) | Repository layout, documentation freshness, and local update policy |

## Repository Facts

- Repository: `blackplume233/game-developers-skills`
- Visibility: private
- Default branch: `master`
- Primary skill root: `skills/`
- Referenced external repositories: `references/`
- Wiki source pages: `wiki/`

## First Skill To Install

Install `skill-repo-manager` first. It manages search, installation, referenced
repositories, README/Wiki synchronization, version checks, privacy audit,
commits, and pushes.

```bash
npx skills add blackplume233/game-developers-skills --skill skill-repo-manager -g -y
```

The source path for that skill is:

```text
skills/skill-management/skill-repo-manager/
```
