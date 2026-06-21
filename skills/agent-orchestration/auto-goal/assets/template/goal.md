# Auto Goal Task

## Goal

<!-- Keep concise. Rewrite the user's request into a detailed, unambiguous Base Goal. Include compact done evidence. Preserve intent. Do not shrink this without user confirmation. -->

- Base Goal:
- Done Evidence:

## Constraints

<!-- Keep concise. Include scope limits, exclusions, language preference, technical requirements, validation commands, artifact directory, dependency policy, safety boundaries, and external blockers. -->

- Language preference:
- Technical requirements:
- Validation commands:
- Artifact/output convention:
- Dependency policy:
- Safety boundaries:

## Execution Guidance

<!-- How each loop should derive a Sub Goal from the Base Goal, execute it, verify it, and update task files. Keep concise. -->

- Re-read this file before every loop.
- Follow repository language preference, technology requirements, validation commands, and artifact conventions.
- Derive exactly one bounded Sub Goal per loop.
- Record loop detail in `loops/loop-XXX.md`.
- Record wrong paths, failed plans, and useful patterns in `references.md`.
- If a Sub Goal is too broad for one loop, create a child Auto Goal task under `child-goals/`.
- Verify the Sub Goal before updating root State.

## State

```yaml
status: draft
updated_at: YYYY-MM-DD
execution_mode: simulated-file-goal
native_goal_id: null
current_loop: null
next_sub_goal: null
last_verified_loop: null
references: references.md
```
