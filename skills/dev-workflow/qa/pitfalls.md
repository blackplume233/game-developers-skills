# QA Pitfalls & Lessons Learned

Hard-won knowledge from real-operation QA work. Read this when debugging unexpected failures or converting exploratory checks into stable regression cases.

## Test The Real Entry

Do not stop at a unit test when the user asked whether the product works. Start the same entry a real user would use: browser URL, desktop app, CLI command, API client, mobile simulator, plugin host, or a documented test harness.

Unit and integration tests are useful for narrowing root cause, but they are not evidence that the user journey works.

## Screenshots Are Evidence

For UI flows, capture screenshots before and after important transitions. A passing assertion without a screenshot is weak evidence when layout, visibility, focus, or disabled states matter.

## Logs Must Be Incremental

Write each step result immediately. If the run crashes halfway through, the partial log should still explain what happened, which evidence was captured, and where execution stopped.

## Separate Environment Failure From Product Failure

If a run fails because the dev server did not start, a fixture is missing, credentials are unavailable, or a third-party sandbox is down, mark it as environment/setup failure. Do not call it a product regression unless the user-facing behavior is actually wrong.

## Avoid Brittle Text Checks

Text checks are useful, but UI copy changes often. Prefer assertions that combine:

- visible state
- user task outcome
- relevant logs or API response
- stable accessibility labels or test ids when available

## Store The Regression Case

When a defect is found and fixed, immediately save a regression case. The case should include:

- the original failure symptom
- setup data
- exact user actions
- expected final state
- cleanup requirements
- evidence from the fixed run

## Keep Test Data Disposable

Use test accounts, seeded records, temp directories, and sandbox services. Do not run destructive scenarios against production data without explicit confirmation.

## Watch For Hidden Async

Many flaky tests are hidden async bugs: background saves, delayed validation, queued jobs, optimistic UI, animations, or eventual consistency. Wait for a meaningful state change, not only a fixed timeout.

## Windows PowerShell Chaining

Windows PowerShell 5 does not support `&&` for chaining commands. Use `;` instead:

```powershell
# Bad: npm run build && npm test
# Good: npm run build; npm test
```
