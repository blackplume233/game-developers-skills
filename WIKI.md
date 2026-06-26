# Game Developers Skills Wiki

## Navigation

- [Home](wiki/Home.md)
- [Installation](wiki/Installation.md)
- [Skill Publishing](wiki/Skill-Publishing.md)
- [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md)
- [Maintenance Rules](wiki/Maintenance-Rules.md)

## Purpose

This file is the root entry point for the in-repository Wiki. Durable workflow
details live under `wiki/` as separate pages so the repository has a real Wiki
surface instead of one growing document.

## Page Map

| Page | Scope |
|------|-------|
| [Home](wiki/Home.md) | Repository overview, page navigation, and first-time orientation |
| [Installation](wiki/Installation.md) | Normal installs, private repository authentication, and troubleshooting |
| [Skill Publishing](wiki/Skill-Publishing.md) | Release gates, version checks, privacy audit, current skill notes including Auto Goal frontmatter state, changelog, commit, and push |
| [Referenced Skill Repositories](wiki/Referenced-Skill-Repositories.md) | External skill repositories managed as submodules |
| [Maintenance Rules](wiki/Maintenance-Rules.md) | Documentation freshness, repository layout, local updates, and operating rules |

## Maintenance Contract

Keep `README.md`, this `WIKI.md`, and the relevant `wiki/*.md` page in sync
when repository behavior changes. The root `WIKI.md` should stay an index; do
not move long process documentation back into this file.

Run the documentation freshness guard before committing behavior-changing
changes:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```
