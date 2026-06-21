---
name: auto-goal
version: 1.0.0
description: File-backed automatic Goal execution for any repository or workspace. Use when the user asks to use auto-goal, Goal mode, native Codex/Claude goal mode with a goal file, file-maintained objectives, self-correcting goals, human-AI goal collaboration, subagent-assisted goal execution, interoperable goals across Codex/Claude/other agents, HTN-style recursive decomposition, HGoal-inspired execution, Ponytail-style minimal implementation review, or SkillOpt-style iterative optimization of goals and procedures.
---

# Auto Goal

Use this skill to turn a user's intent into one file-backed task, then run it through repeated sub-goal loops. `goal.md` stays concise and human-editable; loop details, evidence, subagent reports, and wrong paths live in companion files.

## Read First

1. First follow the host repository's baseline requirements, including any root or directory-level agent instructions, workflow rules, safety rules, language preferences, technical stack requirements, build/test commands, dependency policy, directory conventions, and contribution conventions.
2. Read the user's current request and any supplied goal file path.
3. Read the current `goal.md`, if one is supplied or already exists.
4. Read only task-relevant project files needed to define evidence, constraints, and safe write scope.
5. Inspect local copies or local notes for [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) and [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) when their ideas affect the current goal loop. If local copies are absent or stale, learn from the linked upstream repositories online before applying their patterns.
6. If multiple instruction sources conflict, obey the higher-priority system/developer/user instructions first, then the nearest applicable repository instructions.

## Repository Baseline Capture

Before drafting or updating `goal.md`, identify and record the host repository baseline that constrains this Goal.

Minimum baseline fields:

- Language preference for user-facing replies and durable artifacts.
- Technology stack, framework, runtime, package manager, and version constraints when discoverable.
- Build, test, lint, format, QA, release, or validation commands relevant to the Goal.
- Dependency policy: whether to add dependencies, prefer standard library/native APIs, or use existing project dependencies.
- Directory and artifact conventions, including where generated task files and final outputs belong.
- Safety rules for destructive operations, secrets, external services, network access, and generated assets.
- Contribution style: naming, formatting, documentation, commit/review expectations, and existing code patterns.

Write the concise baseline summary into `goal.md` Constraints or Execution Guidance. Put detailed command evidence, discovered files, and unresolved questions in the active loop or `references.md`.

## Task Directory

- If the user supplies a path, use that path.
- If the user supplies a directory, create or reuse the Auto Goal task files there.
- If the user supplies a `goal.md` path, treat its parent as the task directory.
- If the repository explicitly defines an artifact, output, task-result, or goal-result directory, create or reuse a task directory there.
- If no repository artifact directory is defined, use `.agents/artifact/goal/<date-slug>/`.
- Do not default to planning/specification directories unless the repository explicitly identifies them as the correct artifact location for generated Goal task state.
- If the goal is cross-agent or should survive future sessions, choose a committed or otherwise shared project path and state why it is durable.
- If the goal is local and temporary, place it under the repository's ignored/local runtime area when one exists, or under a clearly named local folder such as `.auto-goal/`.
- Do not store shared goals only in an ignored or machine-local path.
- Do not assume any specific repository layout, task system, or skill system exists.

Use this structure:

```text
<task-dir>/
  goal.md
  references.md
  loops/
    loop-001.md
  evidence/
  subagents/
  child-goals/
```

## Core Goal File

Keep `goal.md` short enough for the user to inspect and edit live. It is the coordination surface, not the full log.

Use `assets/template/goal.md` as the starting shape. A valid `goal.md` includes only:

- `Goal`: the detailed, unambiguous Base Goal and compact done evidence.
- `Constraints`: scope limits, exclusions, safety rules, compatibility needs, repository language preference, and technical requirements.
- `Execution Guidance`: how to split each loop into a sub-goal, follow repository conventions, and verify it.
- `State`: a YAML block with current machine-readable state.

State must be YAML-shaped plain text so Codex, Claude, and humans can edit it without special tooling. Required state keys are `status`, `updated_at`, `execution_mode`, `native_goal_id`, `current_loop`, `next_sub_goal`, `last_verified_loop`, and `references`.

## Workflow

1. Convert the user's request into a detailed, unambiguous goal statement before execution:
   - preserve the user's actual intent
   - expand vague terms into concrete deliverables, boundaries, and success criteria
   - identify assumptions and unknowns
   - ask only when ambiguity would make execution unsafe or likely wrong
2. Capture the repository baseline and decide how it constrains language, technology, validation, directories, dependencies, and safety.
3. Locate or create the Auto Goal task directory.
4. Write the clarified Base Goal and concise repository baseline to `goal.md`; create `references.md`, `loops/`, `evidence/`, and `subagents/` when useful.
5. Try to bridge into a native host Goal mode when available; otherwise record simulated file-backed mode.
6. Run `scripts/validate_goal_file.py <goal.md>` after creation or material edits.
7. For every loop, re-read `goal.md` before doing any work. This is mandatory because the user may edit it while the goal is running.
8. Re-check task-relevant repository baseline files if the loop touches new modules, tools, languages, generated artifacts, or external systems.
9. Review applicable reference patterns:
   - Ponytail: prefer not doing work, existing platform capability, standard library, native feature, installed dependency, or the minimum implementation that satisfies evidence; never cut safety, validation, accessibility, or data-loss handling.
   - SkillOpt: treat loop outcomes as rollout evidence; edit task files with small bounded changes; accept method changes only when the next validation gate improves or a known failure is prevented.
10. Derive one bounded Sub Goal from the Base Goal and current State.
11. Create or update `loops/loop-XXX.md` with:
   - Base Goal slice being addressed
   - Sub Goal
   - repository baseline check for this loop
   - plan
   - execution notes
   - verification
   - result
   - updates to apply back to `goal.md` or `references.md`
12. If the Sub Goal is still too broad, decompose it recursively using the HTN rules below instead of pretending it is executable.
13. Execute the Sub Goal, using subagents when they improve isolation, review, exploration, or parallel progress.
14. Verify whether the Sub Goal actually advances the Base Goal and satisfies the repository baseline.
15. Update files:
   - keep `goal.md` concise: State, next Sub Goal, and any changed constraints or guidance
   - record wrong paths, failed plans, useful patterns, and accepted subagent findings in `references.md`
   - store detailed loop traces in `loops/`
   - store raw evidence in `evidence/`
16. Before claiming completion, require:
   - `goal.md` status is `complete`
   - Base Goal done evidence has current proof
   - latest loop verification passes
   - unresolved wrong paths or failed plans have either been corrected or declared external/non-required
   - the host repository's baseline completion, testing, safety, and review requirements are satisfied

## Native Goal Mode Bridge

After creating or locating the Auto Goal task directory, try to enter the host agent's native Goal mode if the host exposes one. This is a best-effort bridge; never assume it succeeded unless a real native goal id, tool result, or host-visible confirmation exists.

- Codex: if a native `create_goal` capability is available, create one Goal whose objective is to complete the Auto Goal task from the task directory. The native objective must mention the `goal.md` path and require every loop to re-read `goal.md` before acting. Record `execution_mode: native-codex-goal` and the returned id or evidence in `native_goal_id`.
- Claude: if the host exposes a native goal, plan, project, or task execution mode, activate it according to host rules. Record `execution_mode: native-claude-goal` and any host-visible id or evidence in `native_goal_id`.
- Other agents: if no native Goal mode is exposed, simulate Goal mode with `goal.md`, `references.md`, `loops/`, `evidence/`, and `subagents/`. Record `execution_mode: simulated-file-goal` and `native_goal_id: null`.
- If native Goal activation fails, record the failure in `references.md`, keep the files as the source of truth, set `execution_mode: simulated-file-goal`, and continue.
- Do not create more than one native root Goal for the same Auto Goal task unless the user explicitly requests a restart or migration.

## HTN Recursive Decomposition

Use Auto Goal as a lightweight HTN (Hierarchical Task Network) protocol: each Base Goal is decomposed into methods, Sub Goals, and optionally child Auto Goal tasks.

- Treat `goal.md` as the root task node.
- Treat each loop as one selected method for advancing the root.
- Treat each Sub Goal as an executable leaf only if it can be completed and verified in one bounded loop.
- If a Sub Goal needs its own planning, loops, evidence, or user edits, create a child Auto Goal task under `child-goals/<child-slug>/`.
- Each child task has its own `goal.md`, `references.md`, `loops/`, `evidence/`, `subagents/`, and optional `child-goals/`.
- A parent loop that delegates to a child task must record:
  - child task path
  - parent Base Goal slice
  - child Base Goal
  - expected child completion evidence
  - how child completion will update the parent
- Re-read the parent `goal.md` before integrating child results; the user may have changed the parent objective while the child was running.
- Do not mark the parent Sub Goal accepted until the child task's evidence passes and the parent loop verifies that it advances the parent Base Goal.
- Use `$hgoal` for heavy recursive, multi-agent, isolated-workdir execution when available or explicitly requested; otherwise simulate HTN recursion with nested Auto Goal task directories.

## External Reference Review

Use these projects as live references, not as copied doctrine:

- [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail): before implementing a Sub Goal, check whether the best move is to avoid work, reuse platform/stdlib/native/installed capability, or implement the smallest thing that satisfies evidence while preserving safety-critical handling.
- [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt): after each loop, use failed or successful trajectory evidence to make bounded edits to `goal.md`, `references.md`, and future loop policy; do not weaken evidence to make progress look better.

Reference lookup rule:

- Prefer local checked-out repositories, local docs, or prior notes when available and clearly current enough.
- If local references are missing, incomplete, or possibly stale, inspect the linked upstream repositories online.
- Record any reference-derived lesson that affects execution in `references.md`, including source, date, and how it changed the next Sub Goal.

## Collaboration Loop

Use `goal.md` as the live interface between the user and AI.

- Treat user edits to `goal.md` as first-class instructions, subject to higher-priority system and repository rules.
- Re-read `goal.md` at the start of every loop and after any known user edit.
- Re-read relevant repository instructions when the user changes language, target module, output directory, technology, or validation expectations.
- Keep `goal.md` concise; put history and bulky detail in `references.md`, `loops/`, `evidence/`, and `subagents/`.
- When chat and `goal.md` disagree, reconcile the conflict in `goal.md` before continuing.
- Prefer updating task files over leaving important decisions only in chat.
- Keep revisions small enough that the user can inspect and modify them while the goal is running.

## Self-Correction Rules

The agent may edit task files while executing, but edits must be conservative and auditable.

Allowed without extra user confirmation:

- clarify ambiguous wording without changing user intent
- add missing evidence gates
- split a broad plan item into smaller actions
- mark a path as wrong-direction after failed evidence
- add continuation tasks after a failed check
- record newly discovered constraints
- update YAML State at the end of a loop

Requires explicit user confirmation:

- shrinking or replacing the root objective
- deleting a user-written requirement
- marking external approval, credentials, publishing, or destructive operations as complete
- changing safety boundaries or write scope
- destructive filesystem changes

When the current plan is wrong, do not keep retrying it unchanged. Update `references.md` and the current loop with:

1. failed evidence
2. failure class, such as `bad-goal`, `bad-plan`, `bad-evidence`, `missing-prerequisite`, `external-blocker`, or `wrong-direction`
3. changed method or continuation task
4. next verification gate, reflected in `goal.md` State if it changes the next Sub Goal

## HGoal Lessons To Keep

- Keep the root objective intact until evidence proves completion.
- Treat planning and review as evidence for the next cycle, not completion.
- Use concrete gates and completion audits for broad goals.
- Preserve state outside chat so a fresh agent can resume.
- Use isolated subtasks, independent process evidence, or recursive HGoal when the goal is broad enough to need real execution boundaries.
- Every loop should decompose Base Goal into a Sub Goal, execute it, verify it, and only then update root State.
- HTN decomposition is allowed and encouraged when one Sub Goal is still too large; create child Auto Goal tasks rather than overloading one loop.
- If `$hgoal` is explicitly requested or the objective requires recursive multi-agent execution, use `$hgoal` and keep this skill as the human-editable goal file layer.

## Subagent Use

Use subagents liberally when they improve isolation, review quality, exploration, or parallel progress.

- Good subagent tasks include independent research, code review, test design, alternative plan generation, bug reproduction, implementation of a bounded subtask, and verification against the current goal file.
- Give each subagent the current `goal.md` path, relevant loop file, assigned Sub Goal, allowed write scope, expected evidence, and report location under `subagents/`.
- Require subagents to report back in task-file terms: what changed, what evidence passed, what remains uncertain, and whether `goal.md` or `references.md` needs correction.
- Do not let subagent output silently override the goal. Integrate accepted findings into `goal.md`, `references.md`, or the active loop.
- If subagent tools are unavailable, preserve the same boundaries manually: separate the Sub Goal, evidence, and report in task files.

## SkillOPT-Inspired Optimization

Optimize the task files like an editable skill:

- Treat failures as rollout evidence, not embarrassment.
- Edit the smallest useful part of the goal or method.
- Prefer examples, gates, and anti-patterns over vague instruction inflation.
- Keep wrong paths, failed plans, and accepted methods in `references.md`.
- Accept a `goal.md` edit only when it improves the next execution cycle or prevents a known failure.
- Do not optimize by weakening evidence, narrowing the objective, or hiding unresolved work.

## Interoperability Contract

For non-Codex agents:

- `goal.md` plus the latest loop and `references.md` must contain enough context to resume without the chat transcript.
- Put all file paths in repo-relative form where possible.
- Avoid relying on hidden Codex state, MCP-only state, or memory-only conclusions.
- Use explicit fields instead of tool-specific state names.
- When a tool-specific artifact exists, summarize it in Markdown and link to the path.

## Scripts And Assets

- `assets/template/goal.md`: copy or adapt when creating `goal.md`.
- `assets/template/references.md`: copy or adapt when creating `references.md`.
- `assets/template/loop.md`: copy or adapt for each loop file.
- `scripts/validate_goal_file.py`: mechanical Markdown section validator. It does not judge correctness.
