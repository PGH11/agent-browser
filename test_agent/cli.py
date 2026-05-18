"""命令行入口；当前主要用于本地开发调试。"""

from __future__ import annotations

import argparse
import sys

from test_agent.graph.builder import build_graph
from test_agent.models import BrowserUseResult, Report, TestAgentState, TestRequest
from test_agent.settings import DEFAULT_BROWSER, DEFAULT_TIMEOUT_MS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangChain + Playwright 自动化测试 Agent")
    parser.add_argument("--url", default="", help="目标页面 URL。")
    parser.add_argument("--goal", default="", help="自然语言测试目标。")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用无头浏览器运行；默认会打开可见浏览器窗口。",
    )
    parser.add_argument("--browser", default=DEFAULT_BROWSER, choices=["chromium", "firefox", "webkit"])
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS, help="单步超时时间，单位毫秒。")
    parser.add_argument("--max-candidates", type=int, default=80, help="流程测试中最多扫描的候选元素数量。")
    parser.add_argument("--mode", default="auto", choices=["auto", "browser_use"])
    parser.add_argument("--max-links", type=int, default=50, help="跳转巡检最多检查的目标数量。")
    parser.add_argument("--include-cross-origin", action="store_true", help="跳转巡检时包含跨域链接。")
    return parser


def _initial_state(request: TestRequest) -> TestAgentState:
    return {
        "request": request,
        "route": "browser_use",
        "route_reason": "",
        "browser_use_result": BrowserUseResult(),
        "report": Report(passed=False, title="", markdown=""),
        "errors": [],
    }


def run_once(request: TestRequest) -> Report:
    app = build_graph()
    state = app.invoke(
        _initial_state(request),
        config={
            "run_name": "playwright_test_agent",
            "tags": ["cli", "langgraph", "playwright"],
            "metadata": {
                "base_url": request.base_url,
                "browser": request.browser,
                "headed": request.headed,
            },
        },
    )
    return state["report"]


def run_cli() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    url = args.url.strip()
    goal = args.goal.strip()

    if not url and not goal:
        print("自动化测试 Agent 已启动，输入 exit 或 quit 退出。")
        url = input("目标页面 URL：").strip()
        while True:
            goal = input("测试目标：").strip()
            if goal.lower() in {"exit", "quit"}:
                print("已退出。")
                return
            if not goal:
                print("请描述要测试的浏览器行为。")
                continue
            request = TestRequest(
                base_url=url,
                goal=goal,
                headed=not args.headless,
                browser=args.browser,
                timeout_ms=args.timeout_ms,
                max_candidates=args.max_candidates,
                mode=args.mode,
                max_links=args.max_links,
                same_origin_only=not args.include_cross_origin,
            )
            report = run_once(request)
            print(report.markdown)
            print()
    else:
        request = TestRequest(
            base_url=url,
            goal=goal,
            headed=not args.headless,
            browser=args.browser,
            timeout_ms=args.timeout_ms,
            max_candidates=args.max_candidates,
            mode=args.mode,
            max_links=args.max_links,
            same_origin_only=not args.include_cross_origin,
        )
        report = run_once(request)
        print(report.markdown)
