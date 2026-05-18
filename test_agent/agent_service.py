"""面向前端调用的 Agent 服务层。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from test_agent.graph.builder import build_graph
from test_agent.models import (
    BrowserUseResult,
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


def run_frontend_agent(payload: AgentRunRequest) -> AgentRunResponse:
    """把前端请求交给 LangGraph 外层状态机，由状态机判断并执行。"""

    request = TestRequest(
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
    state = _run_langgraph(request)
    report = state["report"]

    return AgentRunResponse(
        success=report.passed,
        route=state["route"],
        title=report.title,
        markdown=report.markdown,
        artifacts=_extract_artifacts(report.markdown),
    )


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


def _initial_state(request: TestRequest) -> TestAgentState:
    return {
        "request": request,
        "route": "browser_use",
        "route_reason": "",
        "task_type": "",
        "test_plan": [],
        "browser_instruction": "",
        "observations": [],
        "evaluation": "",
        "browser_use_result": BrowserUseResult(),
        "report": Report(passed=False, title="", markdown=""),
        "errors": [],
    }


def _extract_artifacts(markdown: str) -> list[str]:
    artifacts: list[str] = []
    for token in markdown.replace("`", " ").split():
        normalized = token.strip()
        if "\\artifacts\\" in normalized or "/artifacts/" in normalized:
            artifacts.append(normalized)
    return artifacts
