#!/usr/bin/env python3
"""Persist game-deconstruction experiences and promote repeated lessons.

The local queue is always available. Notion synchronization requires NOTION_TOKEN
plus a configured data source/database, or NOTION_PARENT_PAGE_ID for first-time setup.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


API_VERSION = os.environ.get("NOTION_VERSION", "2026-03-11")
DATABASE_NAME = "Game Deconstruction Experience"
SCHEMA_VERSION = "1.2.0"
DEFAULT_LOCAL_ROOT = Path("docs/.local/game-deconstruction")
VALID_DOMAINS = {"ai", "abilities-combat", "animation", "rendering", "cross-system", "methodology"}
VALID_OUTCOMES = {"supported", "refuted", "mixed", "unknown"}
EVIDENCE_LEVELS = {"E0", "E1", "E2", "E3", "E4"}
AUTHORIZATION_SCOPES = {"public", "runtime-observation", "user-owned", "authorized-project"}
SOURCE_ARTIFACT_TYPES = {
    "reader-learning-report",
    "public-reference",
    "runtime-experiment",
    "whitebox-evidence-summary",
}
INTERNAL_REVIEW_PATH_PATTERN = re.compile(
    r"(?:^|[/\\])(?:\.internal[/\\])?(?:review|reviews|audit|audits)(?:[/\\]|$)|"
    r"(?:feynman|subagent)[-_ ]*(?:self[-_ ]*)?review",
    re.I,
)
INTERNAL_REVIEW_MARKERS = ("独立费曼审查", "独立费曼验证", "SubAgent Verdict", "未独立验证")
SENSITIVE_KEY_PATTERN = re.compile(r"(?:token|password|passwd|secret|api[_-]?key|private[_-]?key|auth[_-]?header|authorization[_-]?header)", re.I)
SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"(?:secret_|ntn_|sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z]:\\(?:Users|Documents and Settings)\\", re.I),
    re.compile(r"(?:^|\s)/(?:home|Users)/[^\s/]+/"),
]


class ExperienceError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def env(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def clean_id(value: str) -> str:
    return value.replace("-", "").strip()


def local_root() -> Path:
    return Path(env("GAME_DECONSTRUCTION_LOCAL_ROOT") or DEFAULT_LOCAL_ROOT)


def config_path() -> Path:
    return Path(env("GAME_DECONSTRUCTION_NOTION_CONFIG") or local_root() / "notion.json")


def queue_dir() -> Path:
    return Path(env("GAME_DECONSTRUCTION_QUEUE_DIR") or local_root() / "experience-queue")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperienceError(f"无法读取 JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperienceError(f"{path} 顶层必须是 JSON object。")
    return value


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as handle:
        handle.write(serialized)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


@contextmanager
def local_lock(name: str, stale_seconds: int = 900):
    lock_path = local_root() / "locks" / f"{name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists() and time.time() - lock_path.stat().st_mtime > stale_seconds:
        lock_path.unlink()
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ExperienceError(f"另一个 {name} 进程正在运行；停止并发操作。") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()} started={utc_now()}\n".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()


def load_config() -> dict[str, Any]:
    path = config_path()
    return load_json(path) if path.exists() else {}


def save_config(config: dict[str, Any]) -> None:
    write_json_atomic(config_path(), config)


def notion_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = env("NOTION_TOKEN")
    if not token:
        raise ExperienceError("缺少 NOTION_TOKEN；经验已保留在本地队列，尚未同步。")

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": API_VERSION,
        },
    )

    # Only reads and query POSTs are safe to replay. Create-page/database calls
    # deliberately fail on an uncertain response; the next sync first checks the
    # stable fingerprint before attempting another create.
    replay_safe = method == "GET" or path.endswith("/query")
    max_attempts = 4 if replay_safe else 1
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if replay_safe and (exc.code == 429 or 500 <= exc.code < 600):
                if attempt < max_attempts - 1:
                    retry_after = exc.headers.get("Retry-After")
                    delay = min(float(retry_after) if retry_after else 2**attempt, 10.0)
                    time.sleep(delay)
                    continue
            raise ExperienceError(f"Notion API {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            if replay_safe and attempt < max_attempts - 1:
                time.sleep(min(2**attempt, 10))
                continue
            raise ExperienceError(f"Notion API 请求失败: {exc}") from exc
    raise ExperienceError("Notion API 请求重试耗尽。")


def rich_text(content: str) -> list[dict[str, Any]]:
    chunks = [content[i : i + 1900] for i in range(0, len(content), 1900)] or [""]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def database_properties() -> dict[str, Any]:
    return {
        "Name": {"title": {}},
        "Record ID": {"rich_text": {}},
        "Fingerprint": {"rich_text": {}},
        "Kind": {"select": {"options": [{"name": "Experience", "color": "blue"}]}},
        "Game": {"rich_text": {}},
        "Learning Goal": {"rich_text": {}},
        "Design Questions": {"rich_text": {}},
        "Authorization Scope": {"select": {"options": [{"name": value, "color": "gray"} for value in sorted(AUTHORIZATION_SCOPES)]}},
        "Game Version": {"rich_text": {}},
        "Platform": {"rich_text": {}},
        "Engine": {"rich_text": {}},
        "Domains": {"multi_select": {}},
        "Pattern Keys": {"multi_select": {}},
        "Evidence Level": {
            "select": {"options": [{"name": value, "color": "gray"} for value in sorted(EVIDENCE_LEVELS)]}
        },
        "Confidence": {"number": {"format": "number"}},
        "Outcome": {
            "select": {"options": [{"name": value, "color": "gray"} for value in sorted(VALID_OUTCOMES)]}
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Captured", "color": "blue"},
                    {"name": "Eligible", "color": "yellow"},
                    {"name": "Promoted", "color": "green"},
                    {"name": "Conflict", "color": "red"},
                ]
            }
        },
        "Summary": {"rich_text": {}},
        "Occurred At": {"date": {}},
        "Network Safe": {"checkbox": {}},
    }


def validate_data_source(data_source_id: str) -> None:
    source = notion_request("GET", f"/data_sources/{clean_id(data_source_id)}")
    properties = source.get("properties") or {}
    expected = database_properties()
    missing = sorted(set(expected) - set(properties))
    wrong_types = sorted(
        name
        for name, schema in expected.items()
        if name in properties and properties[name].get("type") not in {None, next(iter(schema))}
    )
    title_count = sum(1 for value in properties.values() if value.get("type") == "title")
    if missing or wrong_types or title_count != 1:
        raise ExperienceError(
            "Notion data source schema 不兼容；停止写入。"
            f" missing={missing}, wrong_types={wrong_types}, title_count={title_count}"
        )


def create_database(parent_page_id: str) -> tuple[str, str, str | None]:
    payload = {
        "parent": {"type": "page_id", "page_id": clean_id(parent_page_id)},
        "title": [{"type": "text", "text": {"content": DATABASE_NAME}}],
        "description": [
            {"type": "text", "text": {"content": "Validated experiences learned by game-deconstruction."}}
        ],
        "is_inline": False,
        "initial_data_source": {"properties": database_properties()},
    }
    database = notion_request("POST", "/databases", payload)
    data_sources = database.get("data_sources") or []
    if not data_sources:
        database = notion_request("GET", f"/databases/{clean_id(database['id'])}")
        data_sources = database.get("data_sources") or []
    if not data_sources:
        raise ExperienceError("Notion database 已创建，但响应中没有 data_source_id。")
    return clean_id(database["id"]), clean_id(data_sources[0]["id"]), database.get("url")


def get_data_source_id(auto_create: bool = False) -> tuple[str, bool]:
    configured = env("NOTION_GAME_DECONSTRUCTION_DATA_SOURCE_ID")
    if configured:
        return clean_id(configured), False

    config = load_config()
    if config.get("data_source_id"):
        return clean_id(str(config["data_source_id"])), False

    database_id = env("NOTION_GAME_DECONSTRUCTION_DATABASE_ID") or config.get("database_id")
    if database_id:
        database = notion_request("GET", f"/databases/{clean_id(str(database_id))}")
        sources = database.get("data_sources") or []
        if not sources:
            raise ExperienceError("配置的 Notion database 中没有 data source。")
        config.update({"database_id": clean_id(str(database_id)), "data_source_id": clean_id(sources[0]["id"])})
        save_config(config)
        return config["data_source_id"], False

    if not auto_create:
        raise ExperienceError("未配置 Notion data source；先执行 init。")
    if not env("NOTION_TOKEN"):
        raise ExperienceError("缺少 NOTION_TOKEN；经验已保留在本地队列，尚未同步。")
    parent_page_id = env("NOTION_PARENT_PAGE_ID")
    if not parent_page_id:
        raise ExperienceError("首次初始化需要 NOTION_PARENT_PAGE_ID。")
    new_database_id, source_id, url = create_database(parent_page_id)
    config.update(
        {
            "database_id": new_database_id,
            "data_source_id": source_id,
            "database_url": url,
            "created_at": utc_now(),
            "notion_version": API_VERSION,
        }
    )
    save_config(config)
    return source_id, True


def normalize_lesson(lesson: Any) -> dict[str, Any]:
    if not isinstance(lesson, dict):
        raise ExperienceError("lessons 中每项必须是 object。")
    pattern_key = str(lesson.get("pattern_key") or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,95}", pattern_key):
        raise ExperienceError(f"无效 pattern_key: {pattern_key!r}")
    rule = str(lesson.get("rule") or "").strip()
    if len(rule) < 12:
        raise ExperienceError(f"{pattern_key} 的 rule 过短。")
    outcome = str(lesson.get("outcome") or "unknown").lower()
    if outcome not in VALID_OUTCOMES:
        raise ExperienceError(f"{pattern_key} 的 outcome 无效: {outcome}")
    confidence = float(lesson.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise ExperienceError(f"{pattern_key} 的 confidence 必须在 0..1。")
    return {
        "pattern_key": pattern_key,
        "rule": rule,
        "scope": str(lesson.get("scope") or "").strip(),
        "outcome": outcome,
        "confidence": confidence,
    }


def canonical_payload(record: dict[str, Any]) -> bytes:
    ignored = {"record_id", "fingerprint", "created_at", "network_safe"}
    value = {key: record[key] for key in sorted(record) if key not in ignored}
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def assert_not_internal_review_record(record: dict[str, Any]) -> None:
    source_report = str(record.get("source_report") or "")
    serialized = json.dumps(record, ensure_ascii=False)
    if INTERNAL_REVIEW_PATH_PATTERN.search(source_report):
        raise ExperienceError("内部审查路径不能作为经验来源；请改用最终学习报告或去敏证据摘要。")
    marker = next((value for value in INTERNAL_REVIEW_MARKERS if value in serialized), None)
    if marker:
        raise ExperienceError(f"内部审查内容不能进入经验队列、Notion 或自动晋升: {marker}")


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    assert_not_internal_review_record(record)
    learning = record.get("learning_context")
    if not isinstance(learning, dict) or learning.get("identity") != "game-designer":
        raise ExperienceError("learning_context.identity 必须是 game-designer。")
    learning_goal = str(learning.get("learning_goal") or "").strip()
    if len(learning_goal) < 12:
        raise ExperienceError("learning_context.learning_goal 至少需要 12 个字符。")
    design_questions = [str(value).strip() for value in learning.get("design_questions", []) if str(value).strip()]
    if not design_questions:
        raise ExperienceError("learning_context.design_questions 至少需要一项。")
    authorized_materials = [str(value).strip() for value in learning.get("authorized_materials", []) if str(value).strip()]
    if not authorized_materials:
        raise ExperienceError("learning_context.authorized_materials 至少需要一项。")
    if learning.get("output_use") != "learning-and-prototyping":
        raise ExperienceError("learning_context.output_use 必须是 learning-and-prototyping。")
    authorization_scope = str(record.get("authorization_scope") or "").strip()
    if authorization_scope not in AUTHORIZATION_SCOPES:
        raise ExperienceError(f"无效 authorization_scope: {authorization_scope}")
    designer_takeaways = [str(value).strip() for value in record.get("designer_takeaways", []) if str(value).strip()]
    if not designer_takeaways:
        raise ExperienceError("designer_takeaways 至少需要一项。")
    game = record.get("game")
    if not isinstance(game, dict) or not str(game.get("name") or "").strip():
        raise ExperienceError("game.name 是必填字段。")
    summary = str(record.get("summary") or "").strip()
    if len(summary) < 20:
        raise ExperienceError("summary 至少需要 20 个字符。")
    domains = sorted({str(value).strip().lower() for value in record.get("domains", []) if str(value).strip()})
    invalid_domains = set(domains) - VALID_DOMAINS
    if invalid_domains:
        raise ExperienceError(f"未知 domains: {sorted(invalid_domains)}")
    if not domains:
        raise ExperienceError("至少需要一个 domain。")

    evidence_level = str(record.get("evidence_level") or "E4").upper()
    if evidence_level not in EVIDENCE_LEVELS:
        raise ExperienceError(f"无效 evidence_level: {evidence_level}")
    confidence = float(record.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise ExperienceError("confidence 必须在 0..1。")

    normalized = dict(record)
    normalized["schema_version"] = SCHEMA_VERSION
    normalized["game"] = {
        "name": str(game["name"]).strip(),
        "version": str(game.get("version") or "unknown").strip(),
        "platform": str(game.get("platform") or "unknown").strip(),
        "engine": str(game.get("engine") or "unknown").strip(),
    }
    normalized["learning_context"] = {
        "identity": "game-designer",
        "learning_goal": learning_goal,
        "design_questions": design_questions,
        "authorized_materials": authorized_materials,
        "output_use": "learning-and-prototyping",
    }
    normalized["authorization_scope"] = authorization_scope
    normalized["designer_takeaways"] = designer_takeaways
    normalized["summary"] = summary
    normalized["domains"] = domains
    normalized["evidence_level"] = evidence_level
    normalized["confidence"] = confidence
    normalized["outcome"] = str(record.get("outcome") or "unknown").lower()
    if normalized["outcome"] not in VALID_OUTCOMES:
        raise ExperienceError(f"无效 outcome: {normalized['outcome']}")
    normalized["network_safe"] = bool(record.get("network_safe", False))
    normalized["source_group"] = str(record.get("source_group") or "").strip()
    source_artifact_type = str(record.get("source_artifact_type") or "reader-learning-report").strip().lower()
    if source_artifact_type not in SOURCE_ARTIFACT_TYPES:
        raise ExperienceError(f"无效 source_artifact_type: {source_artifact_type}")
    normalized["source_artifact_type"] = source_artifact_type
    normalized["source_report"] = str(record.get("source_report") or "").strip()
    normalized["lessons"] = [normalize_lesson(value) for value in record.get("lessons", [])]
    if len(normalized["lessons"]) > 100:
        raise ExperienceError("单条经验最多包含 100 个 lessons。")
    normalized["created_at"] = str(record.get("created_at") or utc_now())
    fingerprint = hashlib.sha256(canonical_payload(normalized)).hexdigest()
    normalized["fingerprint"] = fingerprint
    normalized["record_id"] = str(record.get("record_id") or f"exp-{fingerprint[:16]}")
    return normalized


def sensitive_findings(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if SENSITIVE_KEY_PATTERN.search(str(key)) and child not in (None, "", False, []):
                findings.append(f"{child_path}: sensitive key")
            findings.extend(sensitive_findings(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(sensitive_findings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}: sensitive value pattern")
                break
    return findings


def assert_upload_safe(record: dict[str, Any]) -> None:
    assert_not_internal_review_record(record)
    findings = sensitive_findings(record)
    if findings:
        preview = ", ".join(findings[:5])
        raise ExperienceError(f"network_safe 记录疑似包含敏感字段、密钥或本地用户路径；停止上传: {preview}")


def page_title(record: dict[str, Any]) -> str:
    title = f"{record['game']['name']} · {record['summary']}"
    return title[:180]


def create_page(data_source_id: str, record: dict[str, Any]) -> dict[str, Any]:
    pattern_keys = sorted({lesson["pattern_key"] for lesson in record["lessons"]})
    payload_json = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    if len(payload_json.encode("utf-8")) > 180_000:
        raise ExperienceError("经验记录过大，无法安全写入单个 Notion page。请只保留摘要和引用。")
    properties = {
        "Name": {"title": rich_text(page_title(record))},
        "Record ID": {"rich_text": rich_text(record["record_id"])},
        "Fingerprint": {"rich_text": rich_text(record["fingerprint"])},
        "Kind": {"select": {"name": "Experience"}},
        "Game": {"rich_text": rich_text(record["game"]["name"])},
        "Learning Goal": {"rich_text": rich_text(record["learning_context"]["learning_goal"])},
        "Design Questions": {"rich_text": rich_text(" | ".join(record["learning_context"]["design_questions"]))},
        "Authorization Scope": {"select": {"name": record["authorization_scope"]}},
        "Game Version": {"rich_text": rich_text(record["game"]["version"])},
        "Platform": {"rich_text": rich_text(record["game"]["platform"])},
        "Engine": {"rich_text": rich_text(record["game"]["engine"])},
        "Domains": {"multi_select": [{"name": value} for value in record["domains"]]},
        "Pattern Keys": {"multi_select": [{"name": value[:100]} for value in pattern_keys]},
        "Evidence Level": {"select": {"name": record["evidence_level"]}},
        "Confidence": {"number": record["confidence"]},
        "Outcome": {"select": {"name": record["outcome"]}},
        "Status": {"select": {"name": "Captured"}},
        "Summary": {"rich_text": rich_text(record["summary"])},
        "Occurred At": {"date": {"start": record["created_at"]}},
        "Network Safe": {"checkbox": True},
    }
    children = [
        {
            "object": "block",
            "type": "code",
            "code": {"rich_text": rich_text(payload_json), "language": "json", "caption": rich_text("experience-json")},
        }
    ]
    return notion_request(
        "POST",
        "/pages",
        {"parent": {"type": "data_source_id", "data_source_id": data_source_id}, "properties": properties, "children": children},
    )


def text_property(page: dict[str, Any], name: str) -> str:
    prop = page.get("properties", {}).get(name, {})
    values = prop.get("rich_text") or prop.get("title") or []
    return "".join(value.get("plain_text") or value.get("text", {}).get("content", "") for value in values)


def query_pages(data_source_id: str, payload: dict[str, Any] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    query = dict(payload or {})
    query.setdefault("page_size", min(limit or 100, 100))
    while True:
        response = notion_request("POST", f"/data_sources/{data_source_id}/query", query)
        pages.extend(item for item in response.get("results", []) if item.get("object") == "page")
        if limit and len(pages) >= limit:
            return pages[:limit]
        if not response.get("has_more") or not response.get("next_cursor"):
            return pages
        query["start_cursor"] = response["next_cursor"]


def find_by_property(data_source_id: str, property_name: str, value: str) -> list[dict[str, Any]]:
    return query_pages(
        data_source_id,
        {"filter": {"property": property_name, "rich_text": {"equals": value}}, "page_size": 10},
        limit=10,
    )


def retrieve_record(page: dict[str, Any]) -> dict[str, Any]:
    response = notion_request("GET", f"/blocks/{clean_id(page['id'])}/children?page_size=100")
    for block in response.get("results", []):
        code = block.get("code") if block.get("type") == "code" else None
        if not code:
            continue
        content = "".join(item.get("plain_text") or item.get("text", {}).get("content", "") for item in code.get("rich_text", []))
        try:
            record = normalize_record(json.loads(content))
            if text_property(page, "Fingerprint") != record["fingerprint"]:
                raise ExperienceError(f"Notion page {page.get('id')} 的 payload 已被修改，fingerprint 不匹配。")
            if text_property(page, "Record ID") != record["record_id"]:
                raise ExperienceError(f"Notion page {page.get('id')} 的 record_id 与 payload 不匹配。")
            return record
        except (json.JSONDecodeError, ExperienceError):
            continue
    raise ExperienceError(f"Notion page {page.get('id')} 缺少有效 experience-json。")


def queue_record(input_path: Path, destination: Path | None = None) -> tuple[dict[str, Any], Path, bool]:
    record = normalize_record(load_json(input_path))
    target_dir = destination or queue_dir()
    target = target_dir / f"{record['record_id']}.json"
    if target.exists():
        current = normalize_record(load_json(target))
        if current["fingerprint"] != record["fingerprint"]:
            raise ExperienceError(f"record_id 冲突: {record['record_id']}")
        return record, target, False
    write_json_atomic(target, record)
    return record, target, True


def sync_records(source_dir: Path, auto_create: bool = False) -> dict[str, Any]:
    with local_lock("notion-sync"):
        data_source_id, created_database = get_data_source_id(auto_create=auto_create)
        validate_data_source(data_source_id)
        uploaded = 0
        existing = 0
        skipped = 0
        errors: list[dict[str, str]] = []
        for path in sorted(source_dir.glob("*.json")):
            try:
                record = normalize_record(load_json(path))
                if not record["network_safe"]:
                    skipped += 1
                    continue
                assert_upload_safe(record)
                if find_by_property(data_source_id, "Fingerprint", record["fingerprint"]):
                    existing += 1
                    continue
                create_page(data_source_id, record)
                uploaded += 1
            except ExperienceError as exc:
                errors.append({"file": str(path), "error": str(exc)})
    return {
        "ok": not errors,
        "created_database": created_database,
        "data_source_id": data_source_id,
        "uploaded": uploaded,
        "existing": existing,
        "skipped_not_network_safe": skipped,
        "errors": errors,
    }


def recall_records(
    data_source_id: str,
    game: str | None = None,
    domain: str | None = None,
    pattern_key: str | None = None,
    limit: int = 20,
    full: bool = True,
) -> list[dict[str, Any]]:
    validate_data_source(data_source_id)
    filters: list[dict[str, Any]] = []
    if game:
        filters.append({"property": "Game", "rich_text": {"contains": game}})
    if domain:
        filters.append({"property": "Domains", "multi_select": {"contains": domain}})
    if pattern_key:
        filters.append({"property": "Pattern Keys", "multi_select": {"contains": pattern_key}})
    payload: dict[str, Any] = {"sorts": [{"property": "Occurred At", "direction": "descending"}]}
    if len(filters) == 1:
        payload["filter"] = filters[0]
    elif filters:
        payload["filter"] = {"and": filters}
    pages = query_pages(data_source_id, payload, limit=limit)
    if full:
        return [retrieve_record(page) for page in pages]
    return [
        {
            "record_id": text_property(page, "Record ID"),
            "game": text_property(page, "Game"),
            "summary": text_property(page, "Summary"),
            "url": page.get("url"),
        }
        for page in pages
    ]


def load_local_records(source_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(source_dir.glob("*.json")):
        try:
            records.append(normalize_record(load_json(path)))
        except ExperienceError:
            continue
    return records


def normalize_rule(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def pattern_candidates(
    records: Iterable[dict[str, Any]],
    min_support: int,
    min_games: int,
    min_confidence: float,
    consensus_ratio: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = collections.defaultdict(list)
    for record in records:
        for lesson in record.get("lessons", []):
            grouped[lesson["pattern_key"]].append((record, lesson))

    candidates: list[dict[str, Any]] = []
    for pattern_key, entries in sorted(grouped.items()):
        if any(lesson["outcome"] in {"refuted", "mixed"} for _, lesson in entries):
            continue
        supported = [
            (record, lesson)
            for record, lesson in entries
            if lesson["outcome"] == "supported"
            and record["evidence_level"] in {"E0", "E1", "E2"}
            and record.get("source_group")
            and record["network_safe"]
        ]
        deduplicated: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
        for record, lesson in supported:
            key = (record["game"]["name"].casefold(), record["source_group"].casefold())
            current = deduplicated.get(key)
            if not current or current[1]["confidence"] < lesson["confidence"]:
                deduplicated[key] = (record, lesson)
        supported = list(deduplicated.values())
        games = {record["game"]["name"].casefold() for record, _ in supported}
        if len(supported) < min_support or len(games) < min_games:
            continue
        average_confidence = sum(lesson["confidence"] for _, lesson in supported) / len(supported)
        if average_confidence < min_confidence:
            continue
        rules = collections.Counter(normalize_rule(lesson["rule"]) for _, lesson in supported)
        winning_rule, winning_count = rules.most_common(1)[0]
        if winning_count / len(supported) < consensus_ratio:
            continue
        chosen = max(
            (lesson for _, lesson in supported if normalize_rule(lesson["rule"]) == winning_rule),
            key=lambda value: value["confidence"],
        )
        candidates.append(
            {
                "pattern_key": pattern_key,
                "rule": chosen["rule"],
                "scope": chosen["scope"],
                "domains": sorted({domain for record, _ in supported for domain in record["domains"]}),
                "confidence": round(average_confidence, 4),
                "support_count": len(supported),
                "distinct_games": sorted({record["game"]["name"] for record, _ in supported}),
                "source_record_ids": sorted({record["record_id"] for record, _ in supported}),
                "promoted_at": utc_now(),
            }
        )
    return candidates


def learned_paths() -> tuple[Path, Path]:
    references = Path(env("GAME_DECONSTRUCTION_LEARNED_ROOT") or Path(__file__).resolve().parent.parent / "references")
    return references / "learned-patterns.json", references / "learned-patterns.md"


def render_learned_markdown(store: dict[str, Any]) -> str:
    lines = [
        "# 自动学习模式",
        "",
        "> 本文件由 `experience_store.py auto-promote` 生成。不要手工编辑；结论仍需结合当前游戏证据使用。",
        "",
    ]
    patterns = store.get("patterns", [])
    if not patterns:
        lines.extend(["当前尚无达到自动晋升门槛的跨游戏模式。", ""])
        return "\n".join(lines)
    for item in patterns:
        lines.extend(
            [
                f"## {item['pattern_key']}",
                "",
                f"- 规则：{item['rule']}",
                f"- 适用范围：{item.get('scope') or '未限定'}",
                f"- 领域：{', '.join(item.get('domains', []))}",
                f"- 置信度：{item['confidence']:.2f}",
                f"- 支持：{item['support_count']} 条经验 / {len(item['distinct_games'])} 款游戏",
                f"- 游戏：{', '.join(item['distinct_games'])}",
                f"- 晋升时间：{item['promoted_at']}",
                "",
            ]
        )
    return "\n".join(lines)


def _promote_patterns_unlocked(records: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    candidates = pattern_candidates(
        records,
        min_support=args.min_support,
        min_games=args.min_games,
        min_confidence=args.min_confidence,
        consensus_ratio=args.consensus_ratio,
    )
    json_path, markdown_path = learned_paths()
    existing = load_json(json_path) if json_path.exists() else {"schema_version": SCHEMA_VERSION, "revision": 0, "patterns": []}
    by_key = {item["pattern_key"]: item for item in existing.get("patterns", [])}
    changed: list[str] = []
    conflicting_keys = {
        lesson["pattern_key"]
        for record in records
        for lesson in record.get("lessons", [])
        if lesson["outcome"] in {"refuted", "mixed"}
    }
    for pattern_key in sorted(conflicting_keys & set(by_key)):
        del by_key[pattern_key]
        changed.append(f"-{pattern_key}")
    for candidate in candidates:
        current = by_key.get(candidate["pattern_key"])
        if current and current.get("support_count", 0) >= candidate["support_count"] and current.get("confidence", 0) >= candidate["confidence"]:
            continue
        by_key[candidate["pattern_key"]] = candidate
        changed.append(candidate["pattern_key"])
    if changed:
        store = {
            "schema_version": SCHEMA_VERSION,
            "revision": int(existing.get("revision", 0)) + 1,
            "updated_at": utc_now(),
            "policy": {
                "min_support": args.min_support,
                "min_games": args.min_games,
                "min_confidence": args.min_confidence,
                "consensus_ratio": args.consensus_ratio,
                "contradictions_allowed": 0,
            },
            "patterns": sorted(by_key.values(), key=lambda value: value["pattern_key"]),
        }
        if not args.dry_run:
            snapshot = local_root() / "promotion-snapshots" / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            write_json_atomic(snapshot, existing)
            write_json_atomic(json_path, store)
            write_text_atomic(markdown_path, render_learned_markdown(store))
    else:
        store = existing
    return {
        "ok": True,
        "evaluated_records": len(records),
        "eligible_patterns": len(candidates),
        "changed_patterns": changed,
        "revision": store.get("revision", 0),
        "dry_run": args.dry_run,
    }


def promote_patterns(records: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    with local_lock("knowledge-promotion"):
        return _promote_patterns_unlocked(records, args)


def output_json(value: Any, output: str | None = None) -> None:
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


def cmd_init(args: argparse.Namespace) -> int:
    source_id, created = get_data_source_id(auto_create=True)
    validate_data_source(source_id)
    output_json({"ok": True, "created_database": created, "data_source_id": source_id, "config": str(config_path())})
    return 0


def cmd_queue(args: argparse.Namespace) -> int:
    record, path, created = queue_record(Path(args.input), Path(args.queue_dir) if args.queue_dir else None)
    output_json({"ok": True, "created": created, "record_id": record["record_id"], "path": str(path)})
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    result = sync_records(Path(args.queue_dir) if args.queue_dir else queue_dir(), auto_create=args.auto_create)
    output_json(result)
    return 0 if result["ok"] else 1


def cmd_recall(args: argparse.Namespace) -> int:
    source_id, _ = get_data_source_id(auto_create=False)
    records = recall_records(source_id, args.game, args.domain, args.pattern_key, args.limit, full=not args.summary_only)
    output_json({"ok": True, "count": len(records), "records": records}, args.output)
    return 0


def cmd_auto_promote(args: argparse.Namespace) -> int:
    if args.records_dir:
        records = load_local_records(Path(args.records_dir))
    else:
        source_id, _ = get_data_source_id(auto_create=False)
        records = recall_records(source_id, pattern_key=args.pattern_key, limit=args.limit, full=True)
        if len(records) >= args.limit:
            raise ExperienceError("经验查询达到 limit，证据集合可能不完整；停止自动晋升。")
    output_json(promote_patterns(records, args))
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    record, path, created = queue_record(Path(args.input))
    result: dict[str, Any] = {
        "ok": True,
        "queued": {"created": created, "record_id": record["record_id"], "path": str(path)},
    }
    try:
        result["sync"] = sync_records(queue_dir(), auto_create=args.auto_create)
        source_id, _ = get_data_source_id(auto_create=False)
        records = recall_records(source_id, limit=args.limit, full=True)
        if len(records) >= args.limit:
            raise ExperienceError("经验查询达到 limit，证据集合可能不完整；停止自动晋升。")
        result["promotion"] = promote_patterns(records, args)
    except ExperienceError as exc:
        result["remote_deferred"] = str(exc)
        result["promotion_deferred"] = "远程经验集合不可用或不完整；为避免局部样本误学习，本次不自动晋升。"
    output_json(result)
    return 0


def add_promotion_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-support", type=int, default=5)
    parser.add_argument("--min-games", type=int, default=3)
    parser.add_argument("--min-confidence", type=float, default=0.8)
    parser.add_argument("--consensus-ratio", type=float, default=0.8)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create or resolve the Notion experience data source.")
    init_parser.set_defaults(func=cmd_init)

    queue_parser = subparsers.add_parser("queue", help="Validate and add one experience to the local queue.")
    queue_parser.add_argument("--input", required=True)
    queue_parser.add_argument("--queue-dir")
    queue_parser.set_defaults(func=cmd_queue)

    sync_parser = subparsers.add_parser("sync", help="Upload network-safe queued experiences to Notion.")
    sync_parser.add_argument("--queue-dir")
    sync_parser.add_argument("--auto-create", action="store_true")
    sync_parser.set_defaults(func=cmd_sync)

    recall_parser = subparsers.add_parser("recall", help="Retrieve prior experiences from Notion.")
    recall_parser.add_argument("--game")
    recall_parser.add_argument("--domain", choices=sorted(VALID_DOMAINS))
    recall_parser.add_argument("--pattern-key")
    recall_parser.add_argument("--limit", type=int, default=20)
    recall_parser.add_argument("--summary-only", action="store_true")
    recall_parser.add_argument("--output")
    recall_parser.set_defaults(func=cmd_recall)

    promote_parser = subparsers.add_parser("auto-promote", help="Promote repeated, non-conflicting lessons into the skill knowledge layer.")
    promote_parser.add_argument("--records-dir", help="Use local records for offline testing instead of Notion.")
    promote_parser.add_argument("--pattern-key")
    add_promotion_args(promote_parser)
    promote_parser.set_defaults(func=cmd_auto_promote)

    cycle_parser = subparsers.add_parser("cycle", help="Queue, synchronize, and evaluate promotions after one teardown.")
    cycle_parser.add_argument("--input", required=True)
    cycle_parser.add_argument("--auto-create", action="store_true")
    add_promotion_args(cycle_parser)
    cycle_parser.set_defaults(func=cmd_cycle)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except ExperienceError as exc:
        output_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
