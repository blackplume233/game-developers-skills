#!/usr/bin/env python3
"""refresh_cache.py — 扫描技能仓库, 生成/更新 skill-repo-manager 本地缓存.

设计意图:
  skill-repo-manager 采用「本地缓存 + 缺失问用户」的按需检索策略。本地仓库路径
  跨设备可变, 远端 URL 才是稳定锚点。本脚本把仓库技能清单落成本地缓存文件,
  各设备各自运行一次即可, 不依赖写死的绝对路径。

用法:
  python refresh_cache.py                          # 以当前目录为仓库根
  python refresh_cache.py --repo-root <path>       # 指定仓库根
  python refresh_cache.py --repo-url <url>         # 覆盖远端锚点
  python refresh_cache.py --cache-out <path>       # 覆盖缓存输出路径

默认:
  仓库根   = 当前工作目录
  远端锚点 = github.com/blackplume233/game-developers-skills
  缓存输出 = ~/.agents/skills/.skill-repo-cache.json
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

DEFAULT_CACHE = Path.home() / ".agents" / "skills" / ".skill-repo-cache.json"
DEFAULT_REPO_URL = "github.com/blackplume233/game-developers-skills"


def parse_frontmatter(path):
    """极简 frontmatter 解析: 取 name / version / description (支持 >- 折叠)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = text[3:end]
    result = {}
    current = None
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if (line.startswith(" ") or line.startswith("\t")) and current in result:
            result[current] += " " + line.strip()
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("'\"")
            if val.startswith(">-"):
                result[key] = ""
                current = key
                continue
            result[key] = val
            current = key
    return result


def scan_repo(root):
    """递归扫描 skills/**/SKILL.md, 跳过 references 子模块与隐藏目录."""
    skills = []
    for p in sorted(Path(root).rglob("SKILL.md")):
        parts = p.relative_to(root).parts
        if "references" in parts or "node_modules" in parts:
            continue
        if any(seg.startswith(".") for seg in parts[:-1]):
            continue
        front = parse_frontmatter(p)
        # 结构为 skills/<category>/<skill>/SKILL.md; 去掉开头的 skills 段取分类
        category = parts[1] if len(parts) >= 3 and parts[0] == "skills" else (parts[0] if parts else "")
        skills.append({
            "name": front.get("name", p.parent.name),
            "version": front.get("version", "0.0.0"),
            "description": front.get("description", ""),
            "category": category,
            "path": str(p.relative_to(root).parent),
        })
    return skills


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=os.getcwd(), help="技能仓库根目录")
    ap.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="远端仓库锚点 URL")
    ap.add_argument("--cache-out", default=str(DEFAULT_CACHE), help="缓存文件输出路径")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    if not (root / "skills").is_dir():
        sys.exit(f"错误: {root} 下没有 skills/ 目录, 不是技能仓库根")

    skills = scan_repo(root)

    cache = {}
    out = Path(args.cache_out)
    if out.exists():
        try:
            cache = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    cache["repo_url"] = args.repo_url
    cache["local_path"] = str(root)
    cache["last_synced"] = datetime.date.today().isoformat()

    # 保留历史 installed 状态, 避免每次重扫清空安装记录
    old = {s["name"]: s.get("installed", False) for s in cache.get("skills", [])}
    for s in skills:
        s["installed"] = old.get(s["name"], False)
    cache["skills"] = skills

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"缓存已更新: {out} ({len(skills)} 个技能)")


if __name__ == "__main__":
    main()
