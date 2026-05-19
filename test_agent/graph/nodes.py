"""browser-use 版本的 LangGraph 节点。"""

from __future__ import annotations

import re

from test_agent.ai_planner import (
    evaluate_result_with_ai,
    generate_assertions_with_ai,
    generate_plan_with_ai,
    validate_request_with_ai,
)
from test_agent.browser_use_runner import run_browser_use_task
from test_agent.logging_utils import debug_print
from test_agent.models import BrowserUseResult, Report, TestAgentState
from test_agent.page_observer import capture_page_snapshot


def route_request(state: TestAgentState) -> TestAgentState:
    """判断请求是否具备运行 browser-use 的必要信息。"""

    request = state["request"]
    if not request.base_url or not request.goal:
        route = "reject"
        reason = "缺少目标 URL 或自然语言测试目标。"
    else:
        route = "validate"
        reason = "基础字段完整，进入 AI 请求合理性判断。"

    debug_print("route_request", {"route": route, "reason": reason})
    return {**state, "route": route, "route_reason": reason}


def validate_request(state: TestAgentState) -> TestAgentState:
    """Reason：用 AI 判断 URL 和测试目标是否适合启动浏览器执行。"""

    decision = validate_request_with_ai(state["request"])
    if decision["is_valid"]:
        route = "browser_use"
        reason = f"AI 请求判断通过：{decision['reason']}"
    else:
        route = "reject"
        reason = f"AI 请求判断拒绝：{decision['reason']}"

    observations = [*state["observations"], f"Reason：{reason}"]
    debug_print("validate_request", decision)
    return {**state, "route": route, "route_reason": reason, "observations": observations}


def analyze_goal(state: TestAgentState) -> TestAgentState:
    """Reason/Plan：基于用户目标和页面快照动态生成测试计划。"""

    plan_result = generate_plan_with_ai(
        state["request"],
        state["page_snapshot"],
        state["memories"],
    )
    task_type = plan_result["task_type"]
    plan = plan_result["test_plan"]

    observations = [
        f"Reason：识别任务类型为「{task_type}」。",
        f"Reason：用户原始目标为「{state['request'].goal.strip()}」。",
        "Plan：AI 已基于用户目标和页面快照生成动态测试计划。",
    ]
    debug_print("analyze_goal", {"task_type": task_type, "plan": plan})
    return {**state, "task_type": task_type, "test_plan": plan, "observations": [*state["observations"], *observations]}


def observe_page(state: TestAgentState) -> TestAgentState:
    """Observe：在生成测试计划前生成页面快照。"""

    snapshot = capture_page_snapshot(state["request"], state["task_type"])
    if snapshot.success:
        observe_text = (
            "Observe：页面快照完成，"
            f"标题「{snapshot.title or '无标题'}」，"
            f"可交互元素 {len(snapshot.interactive_elements)} 个，"
            f"链接 {len(snapshot.links)} 个。"
        )
    else:
        observe_text = f"Observe：页面快照失败，后续将交给 browser-use 继续观察。原因：{snapshot.error}"
    observations = [*state["observations"], observe_text]
    debug_print("observe_page", snapshot)
    return {**state, "page_snapshot": snapshot, "observations": observations}


def generate_assertions(state: TestAgentState) -> TestAgentState:
    """Assert：根据目标、任务类型和页面快照生成可验证标准。"""

    assertions = generate_assertions_with_ai(
        state["request"],
        state["page_snapshot"],
        state["task_type"],
        state["test_plan"],
    )

    observations = [*state["observations"], f"Assert：已生成 {len(assertions)} 条外层断言。"]
    debug_print("generate_assertions", assertions)
    return {**state, "assertions": assertions, "observations": observations}


def plan_browser_action(state: TestAgentState) -> TestAgentState:
    """Plan：把分析结果整理成 browser-use 更容易执行的任务说明。"""

    request = state["request"]
    page_snapshot = state["page_snapshot"]
    plan_text = "\n".join(f"{index}. {step}" for index, step in enumerate(state["test_plan"], start=1))
    assertion_text = "\n".join(f"{index}. {assertion}" for index, assertion in enumerate(state["assertions"], start=1))
    memory_text = "\n".join(f"- {memory}" for memory in state["memories"]) or "- 暂无同域名历史记忆。"
    snapshot_text = page_snapshot.summary or "页面快照暂无可用摘要。"
    screenshot_text = page_snapshot.screenshot or "无页面快照截图。"
    browser_instruction = (
        f"目标页面：{request.base_url}\n"
        f"任务类型：{state['task_type']}\n"
        f"用户原始测试目标：{request.goal}\n\n"
        "同域名历史记忆：\n"
        f"{memory_text}\n\n"
        "计划前页面快照：\n"
        f"{snapshot_text}\n"
        f"页面快照截图路径：{screenshot_text}\n\n"
        "外层 ReAct 测试计划：\n"
        f"{plan_text}\n\n"
        "外层断言标准：\n"
        f"{assertion_text or '暂无外层断言。'}\n\n"
        "执行要求：\n"
        "0. 必须遵守 browser-use 系统要求的 AgentOutput JSON 格式；不要在 JSON 外输出普通文本。\n"
        "1. 真实打开浏览器并操作页面，不要只根据猜测写结论。\n"
        "2. 每一步都先观察当前页面，再结合计划前页面快照决定下一步动作。\n"
        "3. 如果元素不明显，请优先结合页面截图、可见文本、按钮位置、候选链接、可交互元素快照和 DOM 信息判断。\n"
        "4. 历史记忆只能作为避坑参考，不能改变或扩大用户本次测试目标。\n"
        "5. 如果遇到弹窗、加载、状态变化或跳转，请等待页面稳定后再判断。\n"
        f"6. 如果计划要求处理多个同类目标，最多处理 {request.max_links} 个，并说明实际覆盖数量和未覆盖原因。\n"
        "7. 执行完成后必须逐条对照“外层断言标准”说明通过、失败或不确定。\n"
        "8. 如果任务失败，请明确说明失败发生在哪一步、观察到了什么、可能原因是什么。\n"
        "9. 最终只在 browser-use 的 done/result 字段里用中文总结测试结果、执行步骤、断言验证结果、失败原因和最终 URL。"
    )
    memory_observation = f"Memory：已加载 {len(state['memories'])} 条同域名历史记忆。"
    observations = [*state["observations"], memory_observation, "Plan：已生成面向 browser-use 的浏览器执行指令。"]
    debug_print("plan_browser_action", browser_instruction)
    return {**state, "browser_instruction": browser_instruction, "observations": observations}


def run_browser_use_agent(state: TestAgentState) -> TestAgentState:
    """Act：调用 browser-use 完成浏览器自动化测试。"""

    try:
        request = state["request"]
        instruction = state["browser_instruction"] or request.goal
        executable_request = request.model_copy(update={"goal": instruction})
        result = run_browser_use_task(executable_request)
        errors = state["errors"]
        observations = [
            *state["observations"],
            f"Act：browser-use 执行完成，步数 {result.steps}，成功状态 {result.success}。",
        ]
        markdown = _render_browser_use_report(state, result)
        report = Report(
            passed=result.success,
            title="browser-use 自动化测试报告",
            markdown=markdown,
        )
    except Exception as exc:
        errors = [*state["errors"], f"browser-use 执行失败：{exc}"]
        observations = [*state["observations"], f"Act：browser-use 执行异常：{exc}"]
        report = Report(
            passed=False,
            title="browser-use 执行失败",
            markdown=f"# browser-use 执行失败\n\n{exc}",
        )
        result = state["browser_use_result"]

    debug_print("browser_use_agent", result)
    return {
        **state,
        "browser_use_result": result,
        "report": report,
        "observations": observations,
        "errors": errors,
    }


def evaluate_result(state: TestAgentState) -> TestAgentState:
    """Observe/Evaluate：根据执行结果做外层复核。"""

    result = state["browser_use_result"]
    passed, evaluation, guard_errors = _evaluate_browser_use_result(state, result)
    evaluated_result = result.model_copy(update={"success": passed})
    errors = [*state["errors"], *guard_errors]

    observations = [*state["observations"], evaluation]
    report = Report(
        passed=passed,
        title=state["report"].title or "browser-use 自动化测试报告",
        markdown=_render_browser_use_report(
            {**state, "evaluation": evaluation, "observations": observations, "errors": errors},
            evaluated_result,
        ),
    )
    debug_print("evaluate_result", evaluation)
    return {
        **state,
        "browser_use_result": evaluated_result,
        "evaluation": evaluation,
        "observations": observations,
        "errors": errors,
        "report": report,
    }


def reject_request(state: TestAgentState) -> TestAgentState:
    """请求不适合执行时的安全出口。"""

    reason = state["route_reason"] or "该请求无法作为浏览器测试执行。"
    report = Report(
        passed=False,
        title="测试请求已拒绝",
        markdown=f"# 测试请求已拒绝\n\n{reason}",
    )
    return {**state, "report": report, "errors": [*state["errors"], reason]}


def write_report(state: TestAgentState) -> TestAgentState:
    """最终报告出口。"""

    debug_print("write_report", state["report"])
    return state


def _evaluate_browser_use_result(state: TestAgentState, result: BrowserUseResult) -> tuple[bool, str, list[str]]:
    """先做执行完整性硬保护，再把语义判断交给 AI。"""

    guard_errors: list[str] = []
    final_text = result.final_result.strip()
    lowered_final = final_text.lower()
    lowered_errors = "\n".join(result.errors).lower()
    final_url = result.urls[-1].strip().lower() if result.urls else ""

    if result.errors:
        return False, "Evaluate：browser-use 返回错误信息，外层评估为失败。", guard_errors

    disconnect_markers = [
        "target page, context or browser has been closed",
        "browser has been closed",
        "context has been closed",
        "target closed",
        "page closed",
        "browser disconnected",
        "connection closed",
    ]
    if any(marker in lowered_errors or marker in lowered_final for marker in disconnect_markers):
        guard_errors.append("检测到浏览器页面、上下文或连接被关闭，不能判定为通过。")
        return False, "Evaluate：检测到浏览器中断或页面关闭，外层评估为失败。", guard_errors

    if final_url == "about:blank":
        guard_errors.append("最终 URL 为 about:blank，说明浏览器会话没有停留在有效目标页面。")
        return False, "Evaluate：最终 URL 为 about:blank，外层评估为失败。", guard_errors

    if _is_wait_only_result(final_text):
        guard_errors.append("最终结果只有等待动作，没有实际页面验证结论。")
        return False, "Evaluate：browser-use 只执行了等待，没有产生有效验证证据，外层评估为失败。", guard_errors

    if not final_text:
        guard_errors.append("browser-use 没有返回最终验证文本。")
        return False, "Evaluate：缺少最终验证文本，外层评估为失败。", guard_errors

    ai_evaluation = evaluate_result_with_ai(
        state["request"],
        state["page_snapshot"],
        state["task_type"],
        state["test_plan"],
        state["assertions"],
        result,
    )
    passed = bool(ai_evaluation["passed"])
    confidence = ai_evaluation["confidence"]
    reason = ai_evaluation["reason"]
    failed_assertions = ai_evaluation["failed_assertions"]
    uncertain_points = ai_evaluation["uncertain_points"]

    details: list[str] = [f"Evaluate：AI 外层评估为{'通过' if passed else '失败'}，置信度 {confidence}。{reason}"]
    if failed_assertions:
        details.append("未满足断言：" + "；".join(failed_assertions))
    if uncertain_points:
        details.append("不确定点：" + "；".join(uncertain_points))
    return passed, "\n".join(details), guard_errors


def _is_wait_only_result(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    return bool(re.fullmatch(r"waited\s+for\s+\d+(\.\d+)?\s+seconds?\.?", normalized))


def _render_browser_use_report(state: TestAgentState, result) -> str:
    status = "通过" if result.success else "失败"
    lines = [
        "# browser-use 自动化测试报告",
        "",
        f"测试结果：**{status}**",
        f"任务类型：`{state['task_type'] or '未分类'}`",
        f"执行步数：`{result.steps}`",
    ]
    if result.duration_seconds is not None:
        lines.append(f"耗时：`{result.duration_seconds:.2f}s`")
    if state["test_plan"]:
        lines.extend(["", "## ReAct 测试计划", *[f"{index}. {step}" for index, step in enumerate(state["test_plan"], start=1)]])
    if state["assertions"]:
        lines.extend(["", "## 外层断言标准", *[f"{index}. {assertion}" for index, assertion in enumerate(state["assertions"], start=1)]])
    if state["memories"]:
        lines.extend(["", "## 历史记忆", *[f"- {memory}" for memory in state["memories"]]])
    page_snapshot = state["page_snapshot"]
    if page_snapshot.success or page_snapshot.error:
        lines.extend(["", "## 页面快照"])
        if page_snapshot.title:
            lines.append(f"- 标题：{page_snapshot.title}")
        if page_snapshot.url:
            lines.append(f"- URL：`{page_snapshot.url}`")
        if page_snapshot.screenshot:
            lines.append(f"- 截图：`{page_snapshot.screenshot}`")
        if page_snapshot.viewport:
            lines.append(f"- 视口：{page_snapshot.viewport.get('width')}x{page_snapshot.viewport.get('height')}")
        lines.append(f"- 可交互元素数：{len(page_snapshot.interactive_elements)}")
        if page_snapshot.links:
            lines.append(f"- 页面候选链接数：{len(page_snapshot.links)}")
            lines.extend(f"  - {item}" for item in page_snapshot.links[:30])
        if page_snapshot.visible_text:
            lines.append("- 可见文本摘要：")
            lines.extend(f"  - {item}" for item in page_snapshot.visible_text[:20])
        if page_snapshot.error:
            lines.append(f"- 快照错误：{page_snapshot.error}")
    if state["observations"]:
        lines.extend(["", "## ReAct 轨迹", *[f"- {item}" for item in state["observations"]]])
    if result.urls:
        lines.extend(["", "## 访问过的 URL", *[f"- `{url}`" for url in result.urls]])
    if result.final_result:
        lines.extend(["", "## 最终结果", result.final_result])
    if state["evaluation"]:
        lines.extend(["", "## 外层评估", state["evaluation"]])
    if state["errors"]:
        lines.extend(["", "## 外层错误", *[f"- {error}" for error in state["errors"]]])
    if result.errors:
        lines.extend(["", "## 错误信息", *[f"- {error}" for error in result.errors]])
    if result.screenshots:
        lines.extend(["", "## 截图产物", *[f"- `{path}`" for path in result.screenshots]])
    return "\n".join(lines)
