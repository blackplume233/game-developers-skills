# Maintenance Rules

## Repository Layout

- `README.md`: concise first-time entry point and skill index
- `WIKI.md`: root Wiki index
- `wiki/`: durable Wiki pages
- `CHANGELOG.md`: release history
- `skills/<category>/<skill-name>/`: reusable skills
- `references/<name>/`: external skill repositories as submodules
- `docs/`: focused supporting documentation

## Documentation Freshness

Use `project-wiki-maintainer` whenever a repository change affects usage,
workflow, install commands, skill availability, release process, or repository
layout.

Run before committing behavior-changing changes:

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```

Expected behavior:

- If non-documentation files changed, both `README.md` and `WIKI.md` must also
  be changed.
- If only docs or changelog files changed, the guard does not require README and
  Wiki edits.
- The guard does not inspect every `wiki/*.md` page, so agents must manually
  update the relevant page when a workflow changes.

## Local Skill Updates

After pushing changes to installed skills, update local skill copies:

```bash
npx skills update
```

If `npx skills update` logs failures while returning success, reinstall the
affected skills directly and verify `SKILL.md` versions:

```bash
npx skills add blackplume233/game-developers-skills --skill <skill-name> -g -y
```

## Operating Rules

- Keep every reusable agent capability under `skills/<category>/<skill-name>/`.
- Keep external skill repositories as git submodules under `references/<name>/`.
- Do not vendor-copy referenced repositories into `skills/`.
- Every repository behavior change must update `README.md`, `WIKI.md`, and the
  relevant page under `wiki/`.
- Never publish a skill without version check and AI privacy audit.
