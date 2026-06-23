# Referenced Skill Repositories

External skill repositories are referenced as git submodules under
`references/<name>/`. Do not vendor-copy external repositories into `skills/`.

## Current References

| Name | Source | Path | Notes |
|------|--------|------|-------|
| claude-code-game-studios | https://github.com/donchitos/claude-code-game-studios.git | `references/claude-code-game-studios` | Claude Code 游戏工作室流程技能集合，可通过 `find-skills` 搜索发现 |
| trellis | https://github.com/mindfold-ai/trellis.git | `references/trellis` | Mindfold Trellis AI 工作流系统，可通过 `find-skills` 搜索发现 |

## Add A Reference

Use the helper from the repository root:

```bash
python skills/skill-management/skill-repo-manager/scripts/add_reference_repo.py <git-url-or-local-path> --name <name>
```

For local repository paths, the helper uses Git's per-command
`protocol.file.allow=always` setting so local-path submodules work on modern Git
installations.

## Verify Discovery

After adding a reference, run:

```bash
python skills/skill-management/find-skills/scripts/search_skills.py <keyword>
```

The search helper scans:

- `skills/**/SKILL.md`
- `references/*/**/SKILL.md`
- `skills/*/*/references/*/**/SKILL.md`

If the expected skill is missing, inspect whether the referenced repository has
valid `SKILL.md` frontmatter with at least `name`, `version`, and `description`.

## Commit Scope

When publishing a new reference, stage only submodule metadata and related docs:

```bash
git add .gitmodules references/<reference-name> README.md WIKI.md wiki/ CHANGELOG.md
```
