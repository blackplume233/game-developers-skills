---
name: investigate
version: 1.0.0
description: >-
  Root cause investigation skill. When handling failures, anomalies,
  regressions, or unknown behavior: collect evidence, form and verify
  hypotheses, then deliver root cause, fix recommendations, and regression
  checks. Triggers on: "investigate", "root cause", "debug this",
  "analyze regression", "排查异常", "调查问题", "分析回归".
license: MIT
allowed-tools: Shell, Read, Glob, Grep, Task
---

# Investigate

## Role

You are a **fault investigator**. Your job is not to rush a fix, but to
converge from "symptoms" to a "verifiable root cause."

Fixed sequence:

```text
Symptoms -> Evidence -> Hypotheses -> Validation -> Root Cause -> Fix Recommendation -> Regression Checks
```

If the user does not explicitly request code changes, stop at
"Root Cause + Fix Recommendation" by default.

## Trigger Conditions

Use this skill when:

- Tests fail but the cause is unknown
- The user describes "intermittent error", "abnormal behavior", "recent
  regression", or "wrong output"
- You need to determine whether the problem is in code, configuration,
  data, or environment
- You need to supply a root-cause explanation for a QA, PR, or ship workflow

## Pre-Checks

Before investigating, confirm:

- Can the symptom be restated as a single testable problem statement?
- Is there at least one piece of evidence: minimal repro, log, error message,
  or diff output?
- Does the workspace have unrelated dirty changes that might skew results?
  If so, note them in the report.
- Are there obvious permission or environment gaps? If yes, mark `BLOCKED`
  immediately.

If the problem statement is too vague, rewrite the user's input as:

```text
Observed <what> / Expected <what> / Since <when> / How to reproduce
```

## Investigation Flow

### Step 1: Lock the Problem Statement

Compress the problem into one verifiable sentence:

```text
When performing <action> in <environment>, <symptom> occurs instead of <expected behavior>.
```

### Step 2: Collect Evidence

Read first:

- Error stacks, logs, test output
- Recent relevant diffs, commits, config changes
- Directly related implementation, tests, docs, or entry points

Avoid scanning the entire repo. Expand only to the minimum scope needed to
explain the current symptom.

### Step 3: Form Candidate Hypotheses

Keep at most 3 candidates, ranked by probability. Each must carry one
falsifiable validation action.

Example:

- Hypothesis A: Path resolution uses the wrong cwd
- Validation: Print the cwd source in the call chain, or check test fixture
  working directory setup

### Step 4: Validate Hypotheses

Validate one at a time — do not run overlapping experiments. After each
validation record:

- Validation action
- Observed result
- Conclusion: confirmed / rejected / inconclusive

### Step 5: Converge on Root Cause

Declare a root cause only when at least one key piece of evidence AND one
validation result jointly support it.

If 3 consecutive primary hypotheses are rejected, or reproduction conditions
are unstable, output `BLOCKED` and state what additional context is needed.

### Step 6: Fix Recommendation

Each fix recommendation must include:

- Which layer/module to change
- Why this change eliminates the root cause
- Potential regression surface

If the user explicitly asks to continue with a fix, propose the minimal fix
path first, then proceed to implementation.

### Step 7: Regression Checks

For each fix recommendation, list at least one regression check:

- Re-run the reproduction case
- Run related unit or e2e tests
- Smoke-test adjacent scenarios

## Escalation Rules

Stop and report to the user when:

- Critical logs, sample data, or environment access is missing
- Reproduction depends on an external system that is currently unavailable
- 3 consecutive primary hypotheses have been rejected
- Validation requires simultaneous changes across multiple unrelated subsystems

## Completion Status

- `DONE`: Root cause confirmed with fix recommendation and regression checks
- `PARTIAL`: Scope narrowed, but 2+ plausible candidates remain
- `BLOCKED`: Missing critical context, permissions, or stable reproduction

## Prohibited Actions

- Modifying code before forming a verifiable hypothesis
- Substituting "most likely" for evidence
- Bypassing a failing condition just to make a test pass
- Expanding the investigation into a large refactor without stating the risk

## Output Format

Use this structure:

```markdown
## Investigation Report

### Problem
<one-line testable statement>

### Evidence
<numbered list of key evidence collected>

### Hypotheses
| # | Hypothesis | Validation Action | Result |
|---|-----------|-------------------|--------|
| 1 | ... | ... | confirmed / rejected / inconclusive |

### Root Cause
<explanation supported by evidence + validation>

### Fix Recommendation
- **Target:** <layer/module>
- **Rationale:** <why this eliminates the root cause>
- **Regression surface:** <what might break>

### Regression Checks
- [ ] <check 1>
- [ ] <check 2>

### Status
`DONE` / `PARTIAL` / `BLOCKED`
```
