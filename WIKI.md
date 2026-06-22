# Game Developers Skills Wiki

## Navigation

- [Repository Rules](#repository-rules)
- [Skill Publishing](#skill-publishing)
- [Wiki and README Maintenance](#wiki-and-readme-maintenance)
- [Referenced Skill Repositories](#referenced-skill-repositories)
- [Local Skill Updates](#local-skill-updates)

## Repository Rules

- Keep every reusable agent capability under `skills/<category>/<skill-name>/`.
- Keep external skill repositories as git submodules under `references/<name>/`.
- Do not vendor-copy referenced repositories into `skills/`.
- Every repository behavior change must update `README.md` and this Wiki in the
  same commit, or run the Wiki freshness guard to prove the change is docs-only.

## Skill Publishing

Use `skill-repo-manager` for publishing repository changes. The required gates
are:

1. Version check for changed skills
2. AI privacy audit over every changed skill file
3. Changelog update
4. README and Wiki update
5. Focused git commit
6. Push to the repository remote
7. Local skill update/verification when the changed skill is installed locally

## Wiki and README Maintenance

Use `project-wiki-maintainer` whenever a repository change affects usage,
workflow, install commands, skill availability, release process, or repository
layout.

Run this guard before committing behavior-changing changes:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```

Expected behavior:

- If non-documentation files changed, both `README.md` and `WIKI.md` must also
  be changed.
- If only docs or changelog files changed, the guard does not require README and
  Wiki edits.

## Referenced Skill Repositories

Current references:

| Name | Source | Path | Notes |
|------|--------|------|-------|
| claude-code-game-studios | https://github.com/donchitos/claude-code-game-studios.git | `references/claude-code-game-studios` | Claude Code 游戏工作室流程技能集合，可通过 `find-skills` 搜索发现 |
| trellis | https://github.com/mindfold-ai/trellis.git | `references/trellis` | Mindfold Trellis AI 工作流系统，可通过 `find-skills` 搜索发现 |

Add a reference repository with:

```bash
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <git-url-or-local-path> --name <name>
```

Verify discovery with:

```bash
python skills/skill-management/find-skills/scripts/search_skills.py <keyword>
```

## Local Skill Updates

After pushing changes to installed skills, update local skill copies with:

```bash
npx skills update
```

If `npx skills update` logs failures while returning success, reinstall the
affected skills directly and verify `SKILL.md` versions:

```bash
npx skills add blackplume233/game-developers-skills --skill <skill-name> -g -y
```
