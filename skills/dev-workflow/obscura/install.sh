#!/usr/bin/env bash
# =============================================================================
# Obscura 一键检查并安装脚本
# 适用平台：Windows (Git Bash) / Linux / macOS
# 用法：
#   bash install.sh                 # 默认安装标准渲染版
#   bash install.sh --stealth       # 安装反检测 stealth 版
#   bash install.sh --no-render     # 安装无渲染精简版
#   bash install.sh --force         # 强制重装（跳过"已安装"检查）
#   bash install.sh --version v0.2.0  # 指定版本（默认取 GitHub 最新 release）
#   bash install.sh --dir ~/bin     # 自定义安装目录（默认取 PATH 中首个可写 bin）
# =============================================================================
set -euo pipefail

REPO="h4ckf0r0day/obscura"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"
DOWNLOAD_BASE="https://github.com/${REPO}/releases/download"

# ---------- 参数解析 ----------
VARIANT="standard"     # standard | stealth | no-render
FORCE=0
PINNED_VERSION=""
INSTALL_DIR=""

usage() {
  sed -n '3,9p' "$0" | sed 's/^# //'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stealth)   VARIANT="stealth"; shift ;;
    --no-render) VARIANT="no-render"; shift ;;
    --force)     FORCE=1; shift ;;
    --version)   PINNED_VERSION="$2"; shift 2 ;;
    --dir)       INSTALL_DIR="$2"; shift 2 ;;
    -h|--help)   usage ;;
    *) echo "未知参数: $1"; usage ;;
  esac
done

# ---------- 探测平台与架构 ----------
detect_os() {
  case "$(uname -s)" in
    Linux*)  echo "linux" ;;
    Darwin*) echo "macos" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unsupported" ;;
  esac
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "aarch64" ;;
    *) echo "unsupported" ;;
  esac
}

OS="$(detect_os)"
ARCH="$(detect_arch)"
if [[ "$OS" == "unsupported" || "$ARCH" == "unsupported" ]]; then
  echo "❌ 不支持当前平台/架构: OS=$OS ARCH=$ARCH" >&2
  exit 1
fi
echo "ℹ️  平台: $OS / $ARCH"

# ---------- 确定目标版本 ----------
if [[ -n "$PINNED_VERSION" ]]; then
  VERSION="$PINNED_VERSION"
else
  echo "🔍 查询 GitHub 最新 release..."
  VERSION="$(curl -sfL "$API_URL" | python3 -c "import sys,json;print(json.load(sys.stdin)['tag_name'])" 2>/dev/null \
    || curl -sfL "$API_URL" | grep -oE '"tag_name": *"[^"]+"' | head -1 | grep -oE 'v[0-9.]+')"
  if [[ -z "$VERSION" ]]; then
    echo "❌ 无法获取最新版本号，请用 --version 指定（如 --version v0.2.0）" >&2
    exit 1
  fi
fi
echo "📦 目标版本: $VERSION"

# ---------- 检查是否已安装 ----------
if [[ "$FORCE" -eq 0 ]] && command -v obscura >/dev/null 2>&1; then
  INSTALLED="$(obscura --version 2>/dev/null || echo "unknown")"
  echo "✅ Obscura 已安装: $INSTALLED"
  echo "   （如需重装或升级请加 --force）"
  exit 0
fi

# ---------- 确定安装目录 ----------
if [[ -z "$INSTALL_DIR" ]]; then
  INSTALL_DIR="$HOME/.local/bin"
  # 优先使用 PATH 中已存在的、可写的 bin 目录
  IFS=':' read -ra PATHS <<< "$PATH"
  for p in "${PATHS[@]}"; do
    p="${p%/}"
    # 跳过系统目录与 Git 内置目录
    case "$p" in
      /mingw*|/usr*|/bin|/c/Windows*|/c/Program*|/c/Python*) continue ;;
    esac
    if [[ -d "$p" && -w "$p" ]]; then
      INSTALL_DIR="$p"
      break
    fi
  done
fi
mkdir -p "$INSTALL_DIR"
echo "📁 安装目录: $INSTALL_DIR"

# ---------- 组装资产名并下载 ----------
# 变体后缀：standard='' / stealth='-stealth' / no-render='-no-render'（可叠加）
VARIANT_SUFFIX=""
case "$VARIANT" in
  stealth)   VARIANT_SUFFIX="-stealth" ;;
  no-render) VARIANT_SUFFIX="-no-render" ;;
esac

if [[ "$OS" == "windows" ]]; then
  ASSET="obscura-${ARCH}-windows${VARIANT_SUFFIX}.zip"
  EXTRACT="unzip -o"
else
  ASSET="obscura-${ARCH}-${OS}${VARIANT_SUFFIX}.tar.gz"
  EXTRACT="tar xzf"
fi

URL="${DOWNLOAD_BASE}/${VERSION}/${ASSET}"
TMP_FILE="$(mktemp)"
echo "⬇️  下载: $ASSET"
echo "     来自: $URL"
if ! curl -fL --retry 3 -o "$TMP_FILE" "$URL"; then
  echo "❌ 下载失败，资产可能不存在: $ASSET" >&2
  rm -f "$TMP_FILE"
  exit 1
fi

# ---------- 解压到安装目录 ----------
echo "📂 解压..."
mkdir -p "$INSTALL_DIR/obscura-tmp"
if [[ "$OS" == "windows" ]]; then
  (cd "$INSTALL_DIR/obscura-tmp" && unzip -o "$TMP_FILE")
else
  tar xzf "$TMP_FILE" -C "$INSTALL_DIR/obscura-tmp"
fi

# 移动二进制到安装目录（保留 worker 同目录）
mv -f "$INSTALL_DIR/obscura-tmp/obscura"* "$INSTALL_DIR/" 2>/dev/null || true
rm -rf "$INSTALL_DIR/obscura-tmp"
rm -f "$TMP_FILE"

# ---------- 验证 ----------
BIN="$INSTALL_DIR/obscura"
[[ "$OS" == "windows" ]] && BIN="$INSTALL_DIR/obscura.exe"
if [[ -x "$BIN" ]]; then
  echo "✅ 安装成功: $BIN"
  "$BIN" --version
  echo
  echo "──────────────────────────────────────────────"
  echo "下一步：在 PATH 中加入安装目录即可直接使用"
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
  echo "  或把以下行写入 shell 配置文件（~/.bashrc / ~/.zshrc）"
  echo "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc"
  echo "──────────────────────────────────────────────"
  echo "快速体验：$BIN fetch https://example.com --eval 'document.title'"
else
  echo "❌ 安装后未找到可执行文件: $BIN" >&2
  exit 1
fi
