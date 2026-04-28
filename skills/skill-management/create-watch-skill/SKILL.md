---
name: create-watch-skill
version: 1.0.0
description: "Create a human-in-the-loop watch skill for interactive tools, desktop apps, browser apps, IDE extensions, or E2E debugging workflows. Use when the user wants a new skill similar to watch-vscode: launch an environment, observe a human-driven session, capture evidence, diagnose issues, patch code, rebuild, restart, and continue the feedback loop."
---

# Create Watch Skill

Create a project skill that turns an interactive debugging or QA workflow into a reusable human-machine collaboration loop.

Use this for skills like `watch-vscode`, where the human operates the app and the agent observes, captures evidence, diagnoses failures, fixes code, and relaunches the environment.

## Inputs To Determine

Before writing the new skill, identify:

- Target name: the app, tool, extension, browser flow, CLI TUI, or environment to watch.
- Operator model: whether the human drives the UI, the agent drives the UI, or control switches by phase.
- Launch command: the exact command that opens the target in the required debug mode.
- Observation commands: screenshot, visible text, logs, console output, traces, network events, test artifacts, or telemetry.
- Evidence sources: source paths, log channels, output files, browser devtools, terminal sessions, or MCP tools.
- Repair path: build, typecheck, test, restart, and manual revalidation commands.
- Boundaries: actions the agent must not take without user approval.
- Escalation triggers: phrases or states that mean the user is pointing at the current failure.

If any required command is unknown, inspect the repository for existing debug drivers, QA scripts, Playwright/Electron setup, package scripts, and similar skills before asking the user.

## Skill Shape

Name the new skill with a verb-led `watch-<target>` or `observe-<target>` pattern unless the user requests another name.

Create only:

```text
.agents/skills/<skill-name>/SKILL.md
```

Do not add extra README, changelog, or quick-reference files.

## Required Sections

The generated skill must include these sections.

### Purpose

State the collaboration model in one or two paragraphs:

- The target environment the skill opens.
- The human's role.
- The agent's role.
- The desired loop: observe, diagnose, fix, rebuild, relaunch.

### Launch

List the exact setup and launch commands. Include working directories.

Make the first observation mandatory after launch:

- screenshot or visual snapshot
- visible text or accessibility tree when available
- relevant logs or output channels

### Observation Loop

Define passive observation rules:

- Let the human operate by default.
- Use read-only observation commands to understand state.
- Do not click, type, run commands inside the app, or close the app unless the skill explicitly allows it or the user asks.
- Keep updates short and factual.

Define what to capture when the user says things like "look now", "it failed", "this is the issue", or "watch this".

### Diagnosis And Fix Loop

Define the repair workflow:

1. Capture the current state from all evidence sources.
2. Read relevant source before editing.
3. Form a concrete hypothesis from evidence, not screenshots alone.
4. Patch the smallest relevant code path.
5. Run the target validation commands.
6. Close or reset the old instance if needed.
7. Relaunch a fresh instance.
8. Ask the human to repeat the interaction.

### Mode Boundaries

Be explicit about what the skill is not:

- Not saved QA automation unless the user asks.
- Not autonomous UI driving unless the user grants control.
- Not permission to make broad refactors.
- Not permission to edit external reference repositories unless project rules allow it.

### Project-Specific Rules

Add any repository-specific specs that must be read before edits. For example, if the target repository uses a local spec system, require the generated watch skill to name the relevant spec files before allowing code changes.

## Validation

After creating the skill:

- Check the frontmatter has only `name`, `version`, and `description`.
- Confirm the folder name matches the `name`.
- Confirm all commands include working directories.
- Confirm observation commands are separated from mutating commands.
- Confirm the skill has clear boundaries for human-driven versus agent-driven actions.
- Run a lightweight file read to verify the created `SKILL.md` content.

## Output

Report:

```text
[OK] Created watch skill: <skill-name>
File: .agents/skills/<skill-name>/SKILL.md
Use when: <one sentence>
Requires user-provided details: <none or list>
```
