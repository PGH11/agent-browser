"""测试历史与轻量记忆存储。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from test_agent.models import TestAgentState, TestRequest
from test_agent.settings import TEST_HISTORY_DIR, TEST_HISTORY_FILE, TEST_MEMORY_FILE


MAX_HISTORY_ITEMS = 200
MAX_MEMORY_ITEMS_PER_HOST = 8


def load_memories(request: TestRequest) -> list[str]:
    """读取同域名的历史记忆。"""

    host = _host_key(request.base_url)
    if not host:
        return []
    memory = _read_json(TEST_MEMORY_FILE, default={})
    items = memory.get(host, [])
    return [str(item) for item in items if item]


def list_history(limit: int = 30) -> list[dict[str, Any]]:
    """返回最近的测试历史。"""

    if not TEST_HISTORY_FILE.exists():
        return []
    lines = TEST_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
    items: list[dict[str, Any]] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(items) >= limit:
            break
    return items


def save_history_and_memory(state: TestAgentState, artifacts: list[str]) -> dict[str, Any]:
    """保存一次执行历史，并把可复用结论沉淀为记忆。"""

    TEST_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    request = state["request"]
    result = state["browser_use_result"]
    report = state["report"]
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid4()),
        "created_at": now,
        "url": request.base_url,
        "host": _host_key(request.base_url),
        "goal": _redact_sensitive(request.goal),
        "success": report.passed,
        "route": state["route"],
        "task_type": state["task_type"],
        "steps": result.steps,
        "duration_seconds": result.duration_seconds,
        "final_url": result.urls[-1] if result.urls else "",
        "errors": [_redact_sensitive(error) for error in [*state["errors"], *result.errors]],
        "artifacts": artifacts,
        "evaluation": _redact_sensitive(state["evaluation"]),
        "report_title": report.title,
        "report_markdown": _redact_sensitive(report.markdown),
    }

    with TEST_HISTORY_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")

    _update_memory(item)
    return item


def _update_memory(history_item: dict[str, Any]) -> None:
    host = history_item.get("host")
    if not host:
        return

    memory = _read_json(TEST_MEMORY_FILE, default={})
    items = [str(item) for item in memory.get(host, []) if item]
    summary = _memory_summary(history_item)
    if summary:
        items = [item for item in items if item != summary]
        items.insert(0, summary)
        memory[host] = items[:MAX_MEMORY_ITEMS_PER_HOST]
        TEST_MEMORY_DIR = Path(TEST_MEMORY_FILE).parent
        TEST_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        TEST_MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def _memory_summary(item: dict[str, Any]) -> str:
    status = "成功" if item.get("success") else "失败"
    task_type = item.get("task_type") or "未分类任务"
    goal = _compact(str(item.get("goal") or ""), 80)
    evaluation = _compact(str(item.get("evaluation") or ""), 120)
    final_url = item.get("final_url") or item.get("url") or ""
    if item.get("success"):
        return f"历史成功经验：{task_type}「{goal}」可执行；最终 URL：{final_url}；{evaluation}"
    errors = item.get("errors") or []
    first_error = _compact(str(errors[0]), 120) if errors else "无明确错误信息"
    return f"历史失败经验：{task_type}「{goal}」曾失败；优先规避相同问题：{first_error}"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _host_key(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _compact(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _redact_sensitive(text: str) -> str:
    """脱敏历史中的常见凭证信息。"""

    value = str(text)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", value)
    value = re.sub(
        r"(?i)(password|passwd|pwd|token|api[_-]?key|secret|密码|密钥|凭证)(\s*[:：=,，、]\s*)([^\s,，。；;]+)",
        r"\1\2<redacted>",
        value,
    )
    value = re.sub(r"(?i)(sk|lsv2|ak|rk|ee)[A-Za-z0-9_\-]{16,}", "<secret>", value)
    return value
