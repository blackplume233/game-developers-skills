---
name: obscura
version: 1.0.0
description: 使用 Obscura —— 一个用 Rust 编写的轻量开源无头浏览器（headless browser）—— 进行网页抓取、内容提取、截图、PDF 导出和 AI Agent 自动化。Obscura 支持 V8 真实 JS 渲染、Chrome DevTools Protocol（CDP），可作为 headless Chrome 的直接替代品对接 Puppeteer/Playwright。当用户需要抓网页、爬数据、抓取动态渲染内容、网页截图、防反爬、导出 PDF、或让 AI Agent 浏览/操作网页时使用。本技能会自动检测并安装 obscura 二进制。
---

# Obscura — Rust 无头浏览器

> **自动安装**:本技能使用时会自动检测并安装 `obscura` 二进制（无需手动安装）。详见下方「安装」一节。

**Obscura** 是用 Rust 编写的开源无头浏览器引擎，专为 Web 爬虫和 AI Agent 自动化打造：
- 内置 V8 引擎运行真实 JavaScript
- 支持 Chrome DevTools Protocol（CDP），可作 headless Chrome 的直接替代品
- 兼容 **Puppeteer** 和 **Playwright**
- 轻量（内存 ~30MB，二进制 ~70MB）、启动即时、内置反检测（stealth）
- **不需要 Chromium、Node.js，无任何依赖**，单二进制即可运行
- 开源协议 Apache-2.0，GitHub: https://github.com/h4ckf0r0day/obscura

## 什么时候用它

- 抓取网页内容（HTML / 文本 / Markdown / 链接）
- 抓取需要 JS 渲染的动态页面（SPA、React、反爬前端）
- 网页截图（viewport / 整页）、导出 PDF
- 批量并行爬取（`scrape`）
- 对接 Puppeteer / Playwright 做自动化（CDP server）
- 需要反检测 / 反爬时（stealth 模式、代理）
- AI Agent 需要真实浏览网页、读取 DOM、执行 JS

## 安装（自动）

本技能使用时若检测到 `obscura` 不在 PATH，会**自动下载安装**。

### 检测
```bash
obscura --version
```
已安装则跳过安装。

### 自动安装（脚本逻辑）

**Windows**（当前平台）:
```bash
# 目标目录：C:/Users/<user>/bin（已在 PATH）优先，否则 ~/.local/bin
# 下载 v0.2.0 的 Windows 标准版 zip
curl -sL -o "$TEMP/obscura.zip" \
  "https://github.com/h4ckf0r0day/obscura/releases/download/v0.2.0/obscura-x86_64-windows.zip"
mkdir -p "$HOME/bin"
unzip -o "$TEMP/obscura.zip" -d "$HOME/bin"
# 解压得到 obscura.exe 与 obscura-worker.exe（worker 供 parallel scrape 用，需同目录）
export PATH="$HOME/bin:$PATH"
obscura --version   # 验证
```

**Linux x86_64**:
```bash
curl -sL -o /tmp/obscura.tar.gz \
  "https://github.com/h4ckf0r0day/obscura/releases/download/v0.2.0/obscura-x86_64-linux.tar.gz"
tar xzf /tmp/obscura.tar.gz -C ~/.local/bin
```

**macOS (Apple Silicon)**:
```bash
curl -sL -o /tmp/obscura.tar.gz \
  "https://github.com/h4ckf0r0day/obscura/releases/download/v0.2.0/obscura-aarch64-macos.tar.gz"
tar xzf /tmp/obscura.tar.gz -C ~/.local/bin
```

### Release 资产命名（供选择变体）
最新 tag: `v0.2.0`。资产名模式：`obscura-<arch>-<os>[-stealth][-no-render].zip|.tar.gz`

| 变体 | 说明 | Windows 资产 |
|---|---|---|
| **标准**（默认，含渲染） | 全功能 | `obscura-x86_64-windows.zip` (~51MB) |
| **stealth** | 渲染 + 反检测/TLS 伪装/广告拦截 | `obscura-x86_64-windows-stealth.zip` |
| **no-render** | 无渲染，更小 | `obscura-x86_64-windows-no-render.zip` |
| **no-render-stealth** | 无渲染 + 反检测 | `obscura-x86_64-windows-no-render-stealth.zip` |

> 提示：`stealth` 变体提供更强的反检测能力（TLS 指纹伪装 + tracker 拦截），配合 `--stealth` 参数使用。标准版在 Windows 下运行无额外依赖，开箱即用。

## 核心命令

### 抓取单页
```bash
# 抓取页面标题
obscura fetch https://example.com --eval "document.title"

# 提取所有链接
obscura fetch https://example.com --dump links

# 渲染 JS 后导出 HTML
obscura fetch https://news.ycombinator.com --dump html

# 导出纯文本
obscura fetch https://example.com --dump text

# 导出 Markdown
obscura fetch https://example.com --dump markdown

# 写入文件
obscura fetch https://example.com --dump text --output page.txt

# 流式下载原始响应体（二进制安全，适合图片/JSON/JS/CSS）
obscura fetch https://picsum.photos/200/300 --dump original > photo.jpg

# 等待动态内容
obscura fetch https://example.com --wait-until networkidle0

# 限制超时（慢页面）
obscura fetch https://example.com --timeout 10

# 截图（viewport）
obscura fetch https://example.com --screenshot page.png
# 截图（整页）
obscura fetch https://example.com --screenshot page.png --full-page
```

### 截屏 / 导出 PDF（需渲染变体）
```bash
obscura fetch https://example.com --screenshot page.png
obscura fetch https://example.com --full-page -s page.png
# PDF 见 render 相关，或用 CDP server + Puppeteer
```

### CDP Server（对接 Puppeteer / Playwright）
```bash
obscura serve --port 9222
# 反检测模式
obscura serve --port 9222 --stealth
```

**Puppeteer 连接**:
```javascript
// npm install puppeteer-core
const puppeteer = require('puppeteer-core');
const browser = await puppeteer.connect({
  browserWSEndpoint: 'ws://127.0.0.1:9222/devtools/browser',
});
const page = await browser.newPage();
await page.goto('https://news.ycombinator.com');
console.log(await page.title());
```

**Playwright 连接**:
```javascript
// npm install playwright-core
const { chromium } = require('playwright-core');
const browser = await chromium.connectOverCDP({ endpointURL: 'ws://127.0.0.1:9222' });
const page = await browser.newContext().then(c => c.newPage());
await page.goto('https://en.wikipedia.org/wiki/Web_scraping');
console.log(await page.title());
await browser.close();
```

### 批量并行抓取（scrape）
```bash
# 并行抓取多个 URL
obscura scrape url1 url2 url3 --concurrency 25 --eval "document.querySelector('h1').textContent" --format json

# 静默模式（脚本友好）
obscura scrape https://example.com --quiet --format json

# 抓取从文件读取 URL 列表
obscura fetch --file urls.txt --concurrency 10
```

### 代理 / 反检测
```bash
# 走 HTTP/SOCKS 代理
obscura --proxy socks5://127.0.0.1:1080 fetch https://example.com --dump text

# 全局反检测（对 fetch/serve/scrape/mcp 生效）
obscura --stealth fetch https://example.com --dump html

# 遵守 robots.txt
obscura --obey-robots fetch https://example.com
```

### MCP Server
```bash
# 以 MCP server 模式运行，供支持 MCP 的客户端调用
obscura mcp
```

### 本地开发（内网）
Obscura 默认阻止访问内网/回环地址（SSRF 防护）。本地开发访问 `localhost` 时需显式允许：
```bash
obscura --allow-private-network fetch http://localhost:3000 --dump html
# 或环境变量
export OBSCURA_ALLOW_PRIVATE_NETWORK=1
```

## 常见场景速查

| 场景 | 命令 |
|---|---|
| 抓页面标题 | `obscura fetch URL --eval "document.title"` |
| 抓纯文本 | `obscura fetch URL --dump text` |
| 抓 Markdown | `obscura fetch URL --dump markdown` |
| 抓所有链接 | `obscura fetch URL --dump links` |
| 抓取后 JS 再执行 | `obscura fetch URL --eval "YOUR_JS"` |
| 截图 | `obscura fetch URL --screenshot out.png` |
| 导出 PDF | 走 CDP server + Puppeteer `page.pdf()` |
| 批量抓取 | `obscura scrape url1 url2 --concurrency 25 --format json` |
| 反爬/反检测 | `obscura --stealth fetch URL` 或装 stealth 变体 |
| 走代理 | `obscura --proxy socks5://... fetch URL` |
| 对接 Playwright | `obscura serve --port 9222` + connectOverCDP |
| 对接 Puppeteer | `obscura serve --port 9222` + puppeteer-core connect |

## 注意事项

- **渲染差异**:Obscura 是独立渲染引擎，与 Chromium 在长尾 CSS、部分 Web API、媒体播放、合成器效果、字体光栅化上可能有差异。普通抓取无影响，复杂渲染场景需验证。
- **渲染变体**:截图、整页截图、PDF 需要带渲染（标准/stealth）的变体；`no-render` 变体只能做 DOM/文本级抓取。
- **worker 文件**:解压目录里的 `obscura-worker.exe` 供 `scrape` 并行模式使用，需与主二进制同目录。
- **首次运行**:V8 首次构建/初始化可能稍慢；二进制运行无额外依赖。
- **版本**:当前脚本固定安装 `v0.2.0`；若需最新版，先查 `https://api.github.com/repos/h4ckf0r0day/obscura/releases/latest` 的 `tag_name` 再替换版本号。
- **本地/内网**:默认拦截内网地址，开发用 `--allow-private-network`。
