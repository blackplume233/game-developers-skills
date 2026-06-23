# Installation

## Prerequisites

- Node.js and `npx`
- GitHub access to `blackplume233/game-developers-skills`
- GitHub CLI login for private repository access

Check access before installing:

```bash
gh auth status
gh repo view blackplume233/game-developers-skills --json nameWithOwner,visibility,defaultBranchRef,viewerPermission
```

Expected repository metadata:

- `visibility`: `PRIVATE`
- `defaultBranchRef.name`: `master`
- `viewerPermission`: `ADMIN`, `WRITE`, or another permission with read access

## Install The Recommended Manager

```bash
npx skills add blackplume233/game-developers-skills --skill skill-repo-manager -g -y
```

After installation, restart Codex so the new skill is loaded into the available
skill list.

## Install Other Skills

```bash
# Single global skill
npx skills add blackplume233/game-developers-skills --skill guard -g -y

# All skills
npx skills add blackplume233/game-developers-skills --skill '*' -g -y

# Current project only
npx skills add blackplume233/game-developers-skills --skill qa --skill ship
```

Verify installed skills:

```bash
npx skills list -g --json
```

## Troubleshooting Private Repository Installs

Public GitHub API requests return `404` for this repository without
authentication. Treat `404` from unauthenticated API calls as an auth signal,
not proof that the repository is missing.

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

4. If Codex's bundled installer helper is needed, pass the GitHub token, the
   `master` ref, and the full skill path:

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
