"""面向前端调用的 Agent 服务层。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, Field

from test_agent.graph.builder import build_graph
from test_agent.history_store import list_history, load_memories, save_history_and_memory
from test_agent.models import (
    BrowserUseResult,
    PageSnapshot,
    Report,
    TestAgentState,
    TestRequest,
)
from test_agent.settings import DEFAULT_BROWSER, DEFAULT_TIMEOUT_MS


class AgentRunRequest(BaseModel):
    """前端发送的请求体。"""

    url: str = Field(description="目标页面 URL")
    instruction: str = Field(description="用户自然语言测试目标")
    headed: bool = Field(default=True, description="是否打开可见浏览器")
    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1000, le=120000)
    max_candidates: int = Field(default=120, ge=1, le=300)
    max_links: int = Field(default=50, ge=1, le=500)
    include_cross_origin: bool = Field(default=False)


class AgentRunResponse(BaseModel):
    """返回给前端的响应体。"""

    success: bool
    route: str
    title: str
    markdown: str
    artifacts: list[str] = Field(default_factory=list)
    history_id: str = ""


class AgentHistoryResponse(BaseModel):
    """测试历史列表响应。"""

    items: list[dict] = Field(default_factory=list)


def run_frontend_agent(payload: AgentRunRequest) -> AgentRunResponse:
    """把前端请求交给 LangGraph 外层状态机，由状态机判断并执行。"""

    request = _build_request(payload)
    state = _run_langgraph(request)
    return _build_response_from_state(state)


def stream_frontend_agent(payload: AgentRunRequest) -> Iterator[str]:
    """流式运行 LangGraph，把节点进度逐行推给前端。"""

    request = _build_request(payload)
    app = build_graph()
    state = _initial_state(request)

    yield _json_line(
        {
            "type": "progress",
            "node": "start",
            "message": "已接收请求，准备进入 LangGraph 状态机。",
        }
    )

    try:
        for chunk in app.stream(
            state,
            config={
                "run_name": "frontend_playwright_test_agent_stream",
                "tags": ["frontend", "langgraph", "browser-use", "stream"],
                "metadata": {
                    "base_url": request.base_url,
                    "browser": request.browser,
                    "headed": request.headed,
                    "mode": request.mode,
                },
            },
            stream_mode="updates",
        ):
            if not isinstance(chunk, dict):
                continue
            for node, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                state.update(update)
                yield _json_line(_progress_event(node, state, update))

        response = _build_response_from_state(state)
        yield _json_line({"type": "final", "data": response.model_dump()})
    except Exception as exc:
        yield _json_line(
            {
                "type": "error",
                "message": f"流式执行失败：{exc}",
            }
        )


def get_agent_history(limit: int = 30) -> AgentHistoryResponse:
    """返回最近测试历史。"""

    return AgentHistoryResponse(items=list_history(limit=limit))


def _run_langgraph(request: TestRequest) -> TestAgentState:
    app = build_graph()
    return app.invoke(
        _initial_state(request),
        config={
            "run_name": "frontend_playwright_test_agent",
            "tags": ["frontend", "langgraph", "playwright"],
            "metadata": {
                "base_url": request.base_url,
                "browser": request.browser,
                "headed": request.headed,
                "mode": request.mode,
            },
        },
    )


def _build_request(payload: AgentRunRequest) -> TestRequest:
    return TestRequest(
        base_url=payload.url,
        goal=payload.instruction,
        headed=payload.headed,
        browser=DEFAULT_BROWSER,
        timeout_ms=payload.timeout_ms,
        max_candidates=payload.max_candidates,
        mode="auto",
        max_links=payload.max_links,
        same_origin_only=not payload.include_cross_origin,
    )


def _build_response_from_state(state: TestAgentState) -> AgentRunResponse:
    report = state["report"]
    artifacts = _extract_artifacts(report.markdown)
    history_item = save_history_and_memory(state, artifacts)

    return AgentRunResponse(
        success=report.passed,
        route=state["route"],
        title=report.title,
        markdown=report.markdown,
        artifacts=artifacts,
        history_id=str(history_item.get("id", "")),
    )


def _initial_state(request: TestRequest) -> TestAgentState:
    return {
        "request": request,
        "route": "browser_use",
        "route_reason": "",
        "task_type": "",
        "test_plan": [],
        "assertions": [],
        "browser_instruction": "",
        "memories": load_memories(request),
        "page_snapshot": PageSnapshot(),
        "observations": [],
        "evaluation": "",
        "browser_use_result": BrowserUseResult(),
        "report": Report(passed=False, title="", markdown=""),
        "errors": [],
    }


def _progress_event(node: str, state: TestAgentState, update: dict[str, Any]) -> dict[str, Any]:
    observations = update.get("observations") or []
    latest_observation = observations[-1] if observations else ""
    event: dict[str, Any] = {
        "type": "progress",
        "node": node,
        "message": _node_message(node, state, latest_observation),
    }
    if node == "analyze_goal":
        event["task_type"] = state.get("task_type", "")
        event["test_plan"] = state.get("test_plan", [])
    elif node == "generate_assertions":
        event["assertions"] = state.get("assertions", [])
    elif node == "observe_page":
        snapshot = state.get("page_snapshot")
        if snapshot:
            event["snapshot"] = {
                "success": snapshot.success,
                "title": snapshot.title,
                "url": snapshot.url,
                "screenshot": snapshot.screenshot,
                "interactive_count": len(snapshot.interactive_elements),
                "link_count": len(snapshot.links),
                "error": snapshot.error,
            }
    elif node == "browser_use":
        result = state.get("browser_use_result")
        if result:
            event["browser_use"] = {
                "success": result.success,
                "steps": result.steps,
                "duration_seconds": result.duration_seconds,
                "url_count": len(result.urls),
                "error_count": len(result.errors),
            }
    elif node == "evaluate_result":
        event["evaluation"] = state.get("evaluation", "")
    return event


def _node_message(node: str, state: TestAgentState, latest_observation: str) -> str:
    messages = {
        "route_request": "基础字段检查完成。",
        "validate_request": state.get("route_reason") or "AI 请求合理性判断完成。",
        "observe_page": "页面快照完成，已提取标题、文本、可交互元素和候选链接。",
        "analyze_goal": "AI 已基于用户目标和页面快照生成测试计划。",
        "generate_assertions": "AI 已生成外层断言标准。",
        "plan_browser_action": "已整理 browser-use 执行指令。",
        "browser_use": "browser-use 浏览器执行完成。",
        "evaluate_result": state.get("evaluation") or "外层评估完成。",
        "reject_request": state.get("route_reason") or "请求已拒绝。",
        "write_report": "Markdown 报告已生成。",
    }
    return latest_observation or messages.get(node, f"{node} 完成。")


def _json_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _extract_artifacts(markdown: str) -> list[str]:
    artifacts: list[str] = []
    for token in markdown.replace("`", " ").split():
        normalized = token.strip()
        if "\\artifacts\\" in normalized or "/artifacts/" in normalized:
            artifacts.append(normalized)
    return artifacts
