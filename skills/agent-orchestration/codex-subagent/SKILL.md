---
name: codex-subagent
version: 1.0.0
description: Delegate sub-agent tasks to Codex CLI instead of Cursor built-in sub-agents. Use when you need to spawn a sub-agent for implementation, research, debugging, code review, shell tasks, or any multi-step autonomous work. Does NOT apply to quick readonly codebase exploration (use Cursor built-in explore for that).
---

# Codex Sub-Agent Delegation

Replace Cursor's built-in `Task` tool with `codex exec` for all sub-agent work **except** lightweight codebase exploration.

## When to Delegate to Codex

| Scenario | Use Codex? | Notes |
|----------|-----------|-------|
| Implementation / coding | **Yes** | `--full-auto` |
| Research / investigation | **Yes** | `--full-auto` |
| Debugging | **Yes** | `--full-auto` |
| Code review | **Yes** | Use `codex review` instead |
| Shell / git operations | **Yes** | `--full-auto` |
| Quick file search / grep | **No** | Use Cursor tools directly |
| Readonly codebase exploration | **No** | Use Cursor built-in explore |

## Core Command Pattern

**Critical**: On Windows (PowerShell), always pipe empty stdin to prevent codex from blocking on stdin:

### Standard Task Delegation

```powershell
echo "" | codex exec --full-auto -C "<workspace_root>" "<prompt>"
```

### With Output Capture (recommended for processing results)

```powershell
echo "" | codex exec --full-auto -C "<workspace_root>" -o "$env:TEMP\codex-output.txt" "<prompt>"
```

Then read `$env:TEMP\codex-output.txt` to get the agent's final response.

### Code Review

```powershell
echo "" | codex review --uncommitted
echo "" | codex review --base main
echo "" | codex review --commit <sha>
```

## Execution Protocol

Follow this sequence when delegating to Codex:

### Step 1: Compose the Prompt

Write a self-contained prompt that includes:
- **Goal**: What Codex should accomplish
- **Context**: Relevant file paths, architecture decisions, constraints
- **Deliverable**: What to produce (code changes, analysis, report)
- **Boundaries**: What NOT to touch

The prompt must be self-contained — Codex has no access to your conversation history.

### Step 2: Choose Execution Strategy

**For tasks that modify files** (implementation, refactoring, bug fixes):
```powershell
echo "" | codex exec --full-auto -C "<workspace>" "<prompt>"
```

**For readonly tasks** (research, analysis, investigation):
```powershell
echo "" | codex exec --full-auto -C "<workspace>" -o "$env:TEMP\codex-output.txt" "<prompt>"
```
Then read the output file for results.

**For code review**:
```powershell
echo "" | codex review --uncommitted "<custom_instructions>"
```

### Step 3: Execute via Shell

Use the Shell tool with appropriate `block_until_ms`:
- Simple tasks: 60000 (1 min)
- Medium tasks: 180000 (3 min)
- Complex tasks: 300000 (5 min)

If the task doesn't complete in time, it backgrounds automatically. Use `Await` to poll.

### Step 4: Present Execution Log to User

After Codex finishes, **always** read the terminal output file and present the interaction process to the user. This is mandatory — the user needs to see what Codex did.

1. Read the terminal file (found at the path returned by Shell tool)
2. Extract and display the execution log in a structured format:
   - Show the **session info** (model, sandbox mode)
   - Show each **command Codex executed** and its output
   - Show the **final answer / summary**
   - If files were modified, show `git diff` of the changes
3. Format the log as a collapsible block or code block so it's readable but not overwhelming

## Prompt Templates

### Implementation Task

```
You are working in a monorepo at <workspace>.
Tech stack: <stack details>.

TASK: <description>

RELEVANT FILES:
- <file1>: <purpose>
- <file2>: <purpose>

CONSTRAINTS:
- <constraint1>
- <constraint2>

Implement the changes and ensure the code compiles/passes linting.
```

### Research / Investigation Task

```
You are investigating <topic> in the codebase at <workspace>.

QUESTION: <what to find out>

CONTEXT: <background info>

Produce a concise summary of your findings. Include file paths and line numbers for key references.
```

### Debugging Task

```
BUG: <description of the bug>
REPRODUCTION: <steps or symptoms>

RELEVANT CODE:
- <file>: <what it does>

Find the root cause and fix it. Explain the root cause in your final message.
```

## Long Prompt Handling

For prompts exceeding ~2000 characters, write to a temp file and pipe via stdin (this also solves the stdin blocking issue):

```powershell
Set-Content -Path "$env:TEMP\codex-prompt.md" -Value @"
<long prompt here>
"@
Get-Content "$env:TEMP\codex-prompt.md" | codex exec --full-auto -C "<workspace>"
```

## Parallel Delegation

You can launch multiple Codex tasks in parallel using multiple Shell tool calls, each in its own terminal:

```powershell
# Terminal 1: backend task
echo "" | codex exec --full-auto -C "<workspace>" "Implement the API endpoint for..."

# Terminal 2: frontend task
echo "" | codex exec --full-auto -C "<workspace>" "Build the React component for..."
```

Set `block_until_ms: 0` to immediately background, then poll with `Await`.

**Caution**: Parallel tasks that modify overlapping files may conflict. Use parallel execution only for independent work areas.

## Error Handling

- **Non-zero exit code**: Read terminal output for error details; retry with refined prompt if needed
- **Timeout**: Check if Codex is still running (poll via Await); kill and retry if stuck
- **Wrong changes**: Use `git checkout -- <file>` to revert, then retry with more specific constraints

## Important Notes

- Codex inherits the model from `~/.codex/config.toml` (no need to specify `-m`)
- The workspace is already trusted in Codex config
- Codex operates in its own sandbox — it cannot see your conversation context
- Always provide sufficient context in the prompt for Codex to work independently
