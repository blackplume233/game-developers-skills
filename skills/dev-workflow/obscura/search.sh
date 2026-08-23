#!/usr/bin/env bash
# =============================================================================
# Obscura 快速搜索脚本 —— 给 Agent 的一键搜索路径
# 用法：
#   bash search.sh "关键词"                    # 搜索，默认返回前 5 条
#   bash search.sh --limit 10 "关键词"          # 返回前 10 条
#   bash search.sh "关键词1" "关键词2"          # 依次搜索多个关键词
#   bash search.sh --engine bing "关键词"       # 指定引擎（ddg 默认 / bing；bing 返回跳转链接）
#   bash search.sh --stealth "关键词"           # 反检测模式（Google/Bing 被拦时用）
#   bash search.sh --no-install "关键词"        # 跳过自动安装检查
#   bash search.sh --output out.tsv "关键词"    # 结果写入文件
#   bash search.sh --help
#
# 输出格式（Tab 分隔，Agent 易解析）：标题\t真实URL
# 依赖：obscura 二进制（未装则自动调用 install.sh）、python（用于 URL 编码）
# =============================================================================
set -euo pipefail

ENGINE="ddg"
LIMIT=5
STEALTH=""
NO_INSTALL=0
OUTPUT=""
QUERIES=()
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  sed -n '3,15p' "$0" | sed 's/^#   //'
  exit 0
}

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine)  ENGINE="$2"; shift 2 ;;
    --limit)   LIMIT="$2"; shift 2 ;;
    --stealth) STEALTH="--stealth"; shift ;;
    --no-install) NO_INSTALL=1; shift ;;
    --output)  OUTPUT="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*)        echo "未知参数: $1"; usage ;;
    *)         QUERIES+=("$1"); shift ;;
  esac
done

if [[ ${#QUERIES[@]} -eq 0 ]]; then
  echo "❌ 请提供搜索关键词，如: bash search.sh \"rust 无头浏览器\"" >&2
  exit 1
fi

# ---------- 确保 obscura 可用（自动安装） ----------
if [[ "$NO_INSTALL" -eq 0 ]] && ! command -v obscura >/dev/null 2>&1; then
  echo "🔧 检测到 obscura 未安装，正在自动安装..." >&2
  if [[ -x "$SCRIPT_DIR/install.sh" ]]; then
    bash "$SCRIPT_DIR/install.sh"
  else
    echo "❌ 未找到 install.sh，请先安装 obscura" >&2
    exit 1
  fi
fi
if ! command -v obscura >/dev/null 2>&1; then
  echo "❌ obscura 不可用，安装失败。请手动执行: bash install.sh" >&2
  exit 1
fi

# ---------- URL 编码（支持中文/空格；优先用 python，回退 python3） ----------
PY="$(command -v python || command -v python3 || true)"
urlencode() {
  "$PY" -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"
}
if [[ -z "$PY" ]] || ! "$PY" -c "import urllib.parse" >/dev/null 2>&1; then
  echo "❌ 需要 python 用于 URL 编码" >&2
  exit 1
fi

# ---------- 构造 eval 表达式（提取 标题 + 真实URL） ----------
# 用字面 \t / \n（bash 双反斜杠），避免 printf/命令替换提前展开转义
build_eval() {
  local limit="$1"
  if [[ "$ENGINE" == "bing" ]]; then
    # Bing：<li class="b_algo"><h2><a>
    eval_expr="Array.from(document.querySelectorAll('li.b_algo h2 a')).slice(0,${limit}).map(a=>a.textContent.trim()+'\\t'+a.href).join('\\n')"
  else
    # DuckDuckGo lite：.result-link，uddg 参数藏真实地址，需解码；过滤广告（y.js / ad_domain）
    eval_expr="Array.from(document.querySelectorAll('.result-link')).map(a=>{var m=a.href.match(/uddg=([^&]+)/);return {t:a.textContent.trim(),u:(m?decodeURIComponent(m[1]):a.href),h:a.href}}).filter(r=>r.t!=='more info'&&!r.h.includes('y.js')&&!r.h.includes('ad_domain')).slice(0,${limit}).map(r=>r.t+'\\t'+r.u).join('\\n')"
  fi
}

# ---------- 执行搜索 ----------
declare -a RESULTS=()
for q in "${QUERIES[@]}"; do
  enc="$(urlencode "$q")"
  if [[ "$ENGINE" == "bing" ]]; then
    url="https://www.bing.com/search?q=${enc}"
    wait_flag="--wait-until networkidle0"
  else
    url="https://lite.duckduckgo.com/lite/?q=${enc}"
    wait_flag=""
  fi
  build_eval "$LIMIT"

  echo "🔍 [${ENGINE}] ${q}" >&2
  out="$(obscura $STEALTH fetch "$url" $wait_flag --eval "$eval_expr" --quiet 2>/dev/null || true)"
  # 去掉可能残留的横幅行
  out="$(printf '%s' "$out" | sed '/^Fetching /d' | sed '/^Page loaded:/d')"
  if [[ -n "$out" ]]; then
    RESULTS+=("$out")
  else
    echo "⚠️  ${q}: 无结果（可能被反爬拦截，试试 --engine bing 或 --stealth）" >&2
  fi
done

# ---------- 输出 ----------
if [[ ${#RESULTS[@]} -eq 0 ]]; then
  echo "❌ 搜索无任何结果" >&2
  exit 1
fi

if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "${RESULTS[@]}" > "$OUTPUT"
  echo "✅ 已写入 $OUTPUT（${#RESULTS[@]} 组结果）" >&2
else
  printf '%s\n' "${RESULTS[@]}"
fi
