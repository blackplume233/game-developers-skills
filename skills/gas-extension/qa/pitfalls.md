# Pitfalls & Lessons Learned

Hard-won knowledge from building this E2E infrastructure. Read this when debugging unexpected failures.

## CDP vs Electron: The Critical Difference

**`--remote-debugging-port` does NOT expose the workbench renderer.**

VS Code is an Electron app with multiple processes:
- Main process (Node.js)
- Workbench renderer (the UI you see)
- Extension host (runs extension code)
- WebView renderers (isolated iframe content)

When you use `--remote-debugging-port=9222`, CDP only exposes **WebView renderers**.
The workbench renderer (menus, panels, status bar) is NOT accessible.
Screenshots come back white/blank because you're looking at an empty WebView.

**Solution**: Use Playwright's `_electron.launch()` which connects directly to the Electron main process and gives access to **all** windows including the workbench.

## Instance Conflict: user-data-dir

If VS Code Insiders is already running, launching a new instance with `electron.launch()` causes the new process to delegate to the existing one and immediately exit.
Playwright sees this as "Target page, context or browser has been closed".

**Solution**: Always use `--user-data-dir=<tmpdir>` to create an isolated profile.
This forces VS Code to start a fresh, independent instance.

## Workspace Trust Dialog

Fresh VS Code profiles always show the workspace trust dialog on first open.
This modal blocks all keyboard/command palette interaction.

**Solution**: Pass `--disable-workspace-trust` in launch args.

## ESM vs CJS Mismatch

The vscode-adapter `package.json` has `"type": "module"`. If esbuild outputs CJS (`format: 'cjs'`), VS Code fails to load the extension with:

> Activating extension 'blackplume.game-agent-studio' failed: module is not defined

**Solution**: Set `format: 'esm'` in `esbuild.mjs`. VS Code Insiders 1.100+ supports ESM extensions.

## Windows Path Comparison

`import.meta.url` produces forward-slash paths (`file:///G:/...`) while `fileURLToPath()` returns backslash paths (`G:\...`). Direct comparison fails on Windows.

**Solution**: Compare via `resolve()` which normalizes both:
```typescript
const selfPath = resolve(fileURLToPath(import.meta.url));
const entryPath = process.argv[1] ? resolve(process.argv[1]) : '';
if (selfPath === entryPath) { void main(); }
```

## PowerShell && Operator

PowerShell (not pwsh 7) does not support `&&` for chaining commands. Use `;` instead:
```powershell
# Bad: npx tsc --noEmit && pnpm test:agent
# Good: npx tsc --noEmit; pnpm test:agent
```

## Test Fixture Path Resolution

Tests in `packages/core/src/e2e/` reference fixtures at `packages/core/test-fixtures/codex/`.
The relative path from `src/e2e/` to `test-fixtures/` is `../../../test-fixtures/codex`
(3 levels up: e2e → src → core → then into test-fixtures).

Common mistake: using `../../../../` (4 levels) which causes ENOENT.

## AbortSignal Pre-aborted Edge Case

Node.js `addEventListener('abort', handler)` does NOT fire retroactively if the signal is already aborted when the listener is attached.

```typescript
// Bug: if externalSignal is already aborted, controller never aborts
externalSignal.addEventListener('abort', () => controller.abort(), { once: true });

// Fix: check immediately first
if (externalSignal.aborted) {
  controller.abort();
} else {
  externalSignal.addEventListener('abort', () => controller.abort(), { once: true });
}
```

## Playwright accessibility API Removed

`page.accessibility.snapshot()` was removed in recent Playwright versions.
Use DOM-based alternatives:

```typescript
// Instead of: page.accessibility.snapshot()
// Use:
const text = await page.evaluate(() => document.body.innerText);
```

## Mocha in esbuild: External Warnings

Mocha's parallel worker internals cause esbuild warnings. Add to `external`:

```typescript
external: ['vscode', './reporters/parallel-buffered', './worker.js']
```

## AuditLog.query Filter Gotcha

`AuditFilter` uses `types` (plural array), not `type` (singular string):
```typescript
// Wrong: auditLog.query({ type: 'llm.request' })
// Right: auditLog.query({ types: ['llm.request'] })
```

## codex-acp: exactOptionalPropertyTypes + ACP Client 可选方法

`@agentclientprotocol/sdk` 的 `Client` 用 TS 可选方法语法声明 `readTextFile?(params)`。在启用 `exactOptionalPropertyTypes` 的项目里，写成 `readTextFile: undefined` 会报 TS2375 —— 因为「可选属性」和「值可以是 undefined」不是一回事。

```typescript
// 错：TS2375
const client: Client = {
  sessionUpdate, requestPermission,
  readTextFile: handlers.readTextFile ? (p) => handlers.readTextFile!(p) : undefined,
};

// 对：条件挂载
const client: Client = { sessionUpdate, requestPermission };
if (handlers.readTextFile) client.readTextFile = async (p) => handlers.readTextFile!(p);
```

## codex-acp: Windows spawn 需要 shell: true

`codex-acp` 通过 `npx --yes @zed-industries/codex-acp` 启动。Windows 上 `spawn` 必须传 `shell: true`，否则找不到 `npx.cmd`：

```typescript
spawn(cmd, args, { ..., shell: process.platform === 'win32' });
```

## 本机代理：Responses API，不是 Chat Completions

本机 `rightcode` 代理在 `127.0.0.1:15562/v1` 只实现 **Responses API**（`/v1/responses`，SSE 流），不支持 `/v1/chat/completions`。codex-acp 内部已经用 Responses API 协议与本地代理通信，不要自己再加一层 OpenAI chat completions 客户端——那样只会拿到 `curl: (52) Empty reply from server`。
