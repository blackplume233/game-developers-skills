---
name: project-wiki-maintainer
version: 1.1.0
description: Maintain a repository's project Wiki and README as first-class release artifacts. Use when Codex changes repository behavior, adds or updates skills, changes architecture, modifies installation or usage flows, publishes a repository change, or the user asks to update wiki, README, docs index, project knowledge base, onboarding docs, changelog-adjacent documentation, or documentation freshness gates.
---

# Project Wiki Maintainer

Keep the project Wiki and README synchronized with code, skill, and process
changes. Treat documentation as part of the same change set, not a follow-up.

## Workflow

1. Inspect the repository diff before editing docs.
   - Identify user-visible changes, new commands, new files, changed workflows,
     removed behavior, migration steps, and operational risks.
   - Ignore purely generated artifacts unless they affect how users operate the
     repository.

2. Locate the Wiki target.
   - Prefer an existing in-repo `WIKI.md` as the root Wiki index.
   - Use `wiki/` for durable multi-page Wiki content when the repository needs
     more than one process page.
   - If absent, prefer `docs/wiki.md`, `docs/WIKI.md`, or `wiki/Home.md` if one
     already exists.
   - If no Wiki target exists and the user asked to maintain a project Wiki,
     create `WIKI.md` at the repository root.
   - If a checked-out GitHub wiki repository exists separately, update it only
     when the user explicitly asks or the current repository already documents
     that workflow.

3. Update README and Wiki together.
   - README: keep it concise and entry-point oriented. Update install commands,
     feature tables, repository layout, quickstart, and links.
   - Wiki: keep durable operational knowledge. Include workflows, maintenance
     rules, release gates, troubleshooting, ownership conventions, and links to
     source files. For multi-page Wikis, keep `WIKI.md` as a concise index and
     place long-form pages under `wiki/`.
   - Do not duplicate long content verbatim between README and Wiki. README
     should point to the Wiki for expanded process details.

4. Add a documentation freshness check before commit.

```bash
python skills/dev-workflow/project-wiki-maintainer/scripts/wiki_guard.py --wiki WIKI.md
```

Use `--base <ref>` when checking against a branch or commit other than `HEAD`.
Use `--readme <path>` or `--wiki <path>` if the repository uses non-default
locations.

5. Stage README and Wiki in the same commit as the repository change.

## Wiki Content Rules

- Keep navigation near the top.
- Prefer short sections with concrete commands and file paths.
- Record current repository policies that future agents must obey.
- Include a "Maintenance Rules" section when the Wiki is used as a process
  source of truth.
- Prefer one topic per file under `wiki/` once the Wiki grows beyond a short
  index page.
- Mark known limitations explicitly, especially where tooling returns success
  while logs show partial failure.

## README Content Rules

- Keep README useful for first-time users.
- Update skill/version tables whenever a skill is added or versioned.
- Update install examples when a new recommended skill should be installed.
- Link to the Wiki when process detail would make README too long.

## Failure Conditions

Block or revise the change when:

- The repository behavior changed but neither README nor Wiki changed.
- README documents a capability that the Wiki contradicts.
- Wiki gives maintenance steps that no longer match scripts or repository
  layout.
- A release/publish flow changed but the release checklist was not updated.
