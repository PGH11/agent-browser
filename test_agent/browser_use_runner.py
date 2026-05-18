"""browser-use 执行引擎封装。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from test_agent.models import BrowserUseResult, TestRequest
from test_agent.settings import (
    BROWSER_USE_DOWNLOADS_DIR,
    BROWSER_USE_FORCE_STRUCTURED_OUTPUT,
    BROWSER_USE_TRACES_DIR,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

from browser_use import Agent, BrowserProfile
from browser_use.llm.openai.chat import ChatOpenAI


def run_browser_use_task(request: TestRequest) -> BrowserUseResult:
    """同步入口：运行 browser-use 并返回规整后的结果。"""

    return asyncio.run(_run_browser_use_task(request))


async def _run_browser_use_task(request: TestRequest) -> BrowserUseResult:
    """异步执行 browser-use Agent。"""

    if not OPENAI_API_KEY:
        raise ValueError("未配置 OPENAI_API_KEY、ARK_API_KEY 或 DEFAULT_ARK_API_KEY，无法运行 browser-use。")

    try:
        return await _run_browser_use_task_once(
            request,
            force_structured_output=BROWSER_USE_FORCE_STRUCTURED_OUTPUT,
        )
    except Exception as exc:
        if BROWSER_USE_FORCE_STRUCTURED_OUTPUT and _is_json_schema_unsupported(exc):
            return await _run_browser_use_task_once(request, force_structured_output=False)
        raise


async def _run_browser_use_task_once(request: TestRequest, *, force_structured_output: bool) -> BrowserUseResult:
    """执行一次 browser-use；必要时由上层决定是否降级重试。"""

    llm = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0,
        dont_force_structured_output=not force_structured_output,
        add_schema_to_system_prompt=not force_structured_output,
    )
    profile = BrowserProfile(
        headless=not request.headed,
        downloads_path=Path(BROWSER_USE_DOWNLOADS_DIR),
        traces_dir=Path(BROWSER_USE_TRACES_DIR),
        user_data_dir=Path(BROWSER_USE_TRACES_DIR).parent / "user_data",
    )
    agent = Agent(
        task=_build_task(request),
        llm=llm,
        browser_profile=profile,
        use_vision=True,
        step_timeout=max(30, int(request.timeout_ms / 1000)),
        max_failures=3,
        source="langchain1-browser-use",
    )
    history = await agent.run(max_steps=40)

    raw_errors = _safe_call(history, "errors", default=[]) or []
    errors = [str(error) for error in raw_errors if error is not None]
    raw_success = _safe_call(history, "is_successful", default=None)
    success = bool(raw_success) if raw_success is not None else not bool(errors)

    return BrowserUseResult(
        success=success,
        final_result=str(_safe_call(history, "final_result", default="") or "").strip(),
        errors=errors,
        urls=[str(url) for url in (_safe_call(history, "urls", default=[]) or []) if url is not None],
        screenshots=[str(item) for item in (_safe_call(history, "screenshot_paths", default=[]) or []) if item is not None],
        steps=int(_safe_call(history, "number_of_steps", default=0) or 0),
        duration_seconds=_safe_call(history, "total_duration_seconds", default=None),
    )


def _build_task(request: TestRequest) -> str:
    return (
        f"目标页面：{request.base_url}\n"
        f"用户测试目标：{request.goal}\n\n"
        "重要输出约束：你必须严格遵守 browser-use 系统要求的 AgentOutput JSON 格式；"
        "不要在 JSON 外输出中文说明、Markdown 或普通文本。\n\n"
        "请你作为浏览器自动化测试 Agent 完成任务：\n"
        "1. 打开目标页面。\n"
        "2. 根据用户目标自主判断需要点击、输入、等待或检查的页面元素。\n"
        "3. 如果目标涉及顶部导航、链接跳转、登录、表单或按钮，请真实操作浏览器验证。\n"
        "4. 不要编造结果；如果失败，请说明卡在哪一步、页面表现和可能原因。\n"
        "5. 在 browser-use 最终 done/result 字段里用中文总结测试结果、执行步骤、失败原因和最终 URL。"
    )


def _is_json_schema_unsupported(exc: Exception) -> bool:
    message = str(exc).lower()
    return "json_schema" in message and (
        "not support" in message
        or "not supported" in message
        or "invalidparameter" in message
        or "response_format" in message
    )


def _safe_call(obj: Any, name: str, default: Any) -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return default
    return value
