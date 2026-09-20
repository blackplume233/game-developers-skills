# Installation

## Prerequisites

- Node.js and `npx`
- Network access to GitHub

`blackplume233/game-developers-skills` is **public**, so installing from it
requires no GitHub authentication. A GitHub CLI login is only needed to publish
to this repository, or to install from a repository that really is private.

Confirm what you are installing from:

```bash
gh repo view blackplume233/game-developers-skills --json nameWithOwner,visibility,defaultBranchRef
```

Expected repository metadata:

- `visibility`: `PUBLIC`
- `defaultBranchRef.name`: `master`

## Install The Recommended Manager

```bash
npx skills add blackplume233/game-developers-skills --skill skill-repo-manager -g -y
```

`skill-repo-manager` is configured to treat `blackplume233/game-developers-skills`
as the default skill repository. When a user says "our repository", "the skill
repo", or asks to install/search/publish without naming another source, agents
should use this repository.

After installation, restart Codex so the new skill is loaded into the available
skill list.

## Install Other Skills

```bash
# Single global skill
npx skills add blackplume233/game-developers-skills --skill guard -g -y

# All skills
npx skills add blackplume233/game-developers-skills --skill '*' -g -y

# Current project only: generic QA
npx skills add blackplume233/game-developers-skills --skill qa

# Current project only: project-specific ship workflow
npx skills add blackplume233/game-developers-skills --skill ship

# Global white-box game deconstruction workflow
npx skills add blackplume233/game-developers-skills --skill game-deconstruction -g -y
```

Verify installed skills:

```bash
npx skills list -g --json
```

## Troubleshooting Failed Installs

This repository is public, so unauthenticated API calls against it succeed: a
`404` here means the owner or repository name is wrong, not that you need to log
in. `404` is only an authentication signal when the repository really is private
- check `visibility` before reading anything into it.

If `npx skills add` fails during clone or download:

1. Confirm GitHub CLI can see the repository:

   ```bash
   gh repo view blackplume233/game-developers-skills --json nameWithOwner,visibility,defaultBranchRef,viewerPermission
   ```

2. Configure Git to use GitHub CLI credentials for HTTPS:

   ```bash
   gh auth setup-git
   ```

3. If SSH host key verification blocks cloning, record GitHub's host key once:

   ```bash
   git -c core.sshCommand="ssh -o StrictHostKeyChecking=accept-new" ls-remote git@github.com:blackplume233/game-developers-skills.git
   ```

4. If Codex's bundled installer helper is needed, pass the `master` ref and the
   full skill path. The token is optional for this public repository, and worth
   supplying to avoid anonymous API rate limits:

   ```bash
   $env:GH_TOKEN = gh auth token
   python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py `
     --repo blackplume233/game-developers-skills `
     --path skills/skill-management/skill-repo-manager `
     --ref master `
     --method download
   ```

Do not use the root path `skill-repo-manager`; that path does not exist in this
repository.

## Installing From A Genuinely Private Repository

Different situation, different symptom. If the target repository is private, the
unauthenticated clone fails or asks for credentials, and the API returns `404`.
Authenticate first, then repeat the same install command:

```bash
gh auth status
gh auth setup-git          # let git reuse the GitHub CLI credentials over HTTPS
```

Everything else on this page - paths, refs, the Codex installer helper - applies
unchanged.
