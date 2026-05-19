"""browser-use 版本的数据协议与 LangGraph 状态定义。"""

from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


BrowserName = Literal["chromium", "firefox", "webkit"]
TestMode = Literal["auto", "browser_use"]


class TestRequest(BaseModel):
    """前端或调用方传入的测试请求。"""

    base_url: str = Field(default="", description="目标网站或应用 URL。")
    goal: str = Field(description="用户的自然语言测试目标。")
    headed: bool = Field(default=True, description="是否以有头模式打开浏览器。")
    browser: BrowserName = Field(default="chromium", description="浏览器类型。")
    timeout_ms: int = Field(default=10000, ge=1000, le=120000)
    max_candidates: int = Field(default=120, ge=1, le=300)
    mode: TestMode = Field(default="auto", description="测试模式。")
    max_links: int = Field(default=50, ge=1, le=500)
    same_origin_only: bool = Field(default=True)


class BrowserUseResult(BaseModel):
    """browser-use 执行结果。"""

    success: bool = False
    final_result: str = ""
    errors: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    steps: int = 0
    duration_seconds: float | None = None


class Report(BaseModel):
    """最终返回给用户的测试报告。"""

    passed: bool
    title: str
    markdown: str


class PageSnapshotElement(BaseModel):
    """页面快照中的可交互元素。"""

    tag: str = ""
    role: str = ""
    section: str = "main"
    text: str = ""
    href: str = ""
    aria_label: str = ""
    placeholder: str = ""
    input_type: str = ""
    visible: bool = True
    bbox: dict[str, float] = Field(default_factory=dict)


class PageSnapshot(BaseModel):
    """测试计划前的页面结构快照。"""

    success: bool = False
    url: str = ""
    title: str = ""
    screenshot: str = ""
    summary: str = ""
    viewport: dict[str, int] = Field(default_factory=dict)
    scroll: dict[str, float] = Field(default_factory=dict)
    visible_text: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    footer_links: list[str] = Field(default_factory=list)
    interactive_elements: list[PageSnapshotElement] = Field(default_factory=list)
    error: str = ""


class TestAgentState(TypedDict):
    """LangGraph 全局状态。"""

    request: TestRequest
    route: Literal["validate", "browser_use", "reject"]
    route_reason: str
    task_type: str
    test_plan: list[str]
    assertions: list[str]
    browser_instruction: str
    memories: list[str]
    page_snapshot: PageSnapshot
    observations: list[str]
    evaluation: str
    browser_use_result: BrowserUseResult
    report: Report
    errors: list[str]
