"""browser-use 版本的 LangGraph 节点。"""

from __future__ import annotations

from test_agent.browser_use_runner import run_browser_use_task
from test_agent.logging_utils import debug_print
from test_agent.models import Report, TestAgentState


def route_request(state: TestAgentState) -> TestAgentState:
    """判断请求是否具备运行 browser-use 的必要信息。"""

    request = state["request"]
    if not request.base_url or not request.goal:
        route = "reject"
        reason = "缺少目标 URL 或自然语言测试目标。"
    else:
        route = "browser_use"
        reason = "请求有效，交给 browser-use 执行。"

    debug_print("route_request", {"route": route, "reason": reason})
    return {**state, "route": route, "route_reason": reason}


def analyze_goal(state: TestAgentState) -> TestAgentState:
    """Reason：分析用户目标，判断任务类型和关注点。"""

    goal = state["request"].goal.strip()
    lowered = goal.lower()

    if any(keyword in lowered for keyword in ["login", "登录", "登陆", "sign in"]):
        task_type = "登录/认证测试"
        plan = [
            "打开目标页面并等待首屏加载完成。",
            "识别登录入口，必要时处理弹窗、菜单或跳转。",
            "根据用户提供的凭证填写账号和密码。",
            "提交登录表单并等待页面状态变化。",
            "观察登录后页面、头像、按钮、弹窗或 URL 变化，判断是否登录成功。",
        ]
    elif any(keyword in lowered for keyword in ["导航", "顶部", "跳转", "链接", "nav", "menu"]):
        task_type = "导航/跳转巡检"
        plan = [
            "打开目标页面并识别主要导航区域。",
            "逐个检查用户目标中要求的导航项、按钮或链接。",
            "点击可跳转入口并观察 URL、页面标题或主要内容是否变化。",
            "记录异常链接、无法点击项、空跳转或错误页面。",
        ]
    elif any(keyword in lowered for keyword in ["表单", "提交", "输入", "搜索", "form", "search"]):
        task_type = "表单/输入测试"
        plan = [
            "打开目标页面并定位目标表单或输入区域。",
            "根据用户目标填写必要字段。",
            "提交表单或触发搜索。",
            "观察校验提示、结果区域、URL 或页面状态，判断是否符合预期。",
        ]
    else:
        task_type = "通用页面行为测试"
        plan = [
            "打开目标页面并理解当前页面结构。",
            "根据用户目标定位相关按钮、链接、输入框或页面区域。",
            "执行必要的点击、输入、等待或检查动作。",
            "根据页面可见变化、URL、文本或错误提示判断测试结果。",
        ]

    observations = [
        f"Reason：识别任务类型为「{task_type}」。",
        f"Reason：用户原始目标为「{goal}」。",
    ]
    debug_print("analyze_goal", {"task_type": task_type, "plan": plan})
    return {**state, "task_type": task_type, "test_plan": plan, "observations": observations}


def plan_browser_action(state: TestAgentState) -> TestAgentState:
    """Plan：把分析结果整理成 browser-use 更容易执行的任务说明。"""

    request = state["request"]
    plan_text = "\n".join(f"{index}. {step}" for index, step in enumerate(state["test_plan"], start=1))
    browser_instruction = (
        f"目标页面：{request.base_url}\n"
        f"任务类型：{state['task_type']}\n"
        f"用户原始测试目标：{request.goal}\n\n"
        "外层 ReAct 测试计划：\n"
        f"{plan_text}\n\n"
        "执行要求：\n"
        "0. 必须遵守 browser-use 系统要求的 AgentOutput JSON 格式；不要在 JSON 外输出普通文本。\n"
        "1. 真实打开浏览器并操作页面，不要只根据猜测写结论。\n"
        "2. 每一步都先观察当前页面，再决定下一步动作。\n"
        "3. 如果元素不明显，请优先结合页面截图、可见文本、按钮位置和 DOM 信息判断。\n"
        "4. 如果遇到弹窗、加载、登录态变化或跳转，请等待页面稳定后再判断。\n"
        "5. 如果任务失败，请明确说明失败发生在哪一步、观察到了什么、可能原因是什么。\n"
        "6. 最终只在 browser-use 的 done/result 字段里用中文总结测试结果、执行步骤、验证依据、失败原因和最终 URL。"
    )
    observations = [*state["observations"], "Plan：已生成面向 browser-use 的浏览器执行指令。"]
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
    if result.success:
        evaluation = "Evaluate：browser-use 返回成功，且没有阻断性错误，外层评估为通过。"
    elif result.errors:
        evaluation = "Evaluate：browser-use 返回失败并包含错误信息，外层评估为失败。"
    elif result.final_result:
        evaluation = "Evaluate：browser-use 未明确返回成功，外层根据最终结果保守评估为失败，需要人工复核。"
    else:
        evaluation = "Evaluate：没有获得有效执行结果，外层评估为失败。"

    observations = [*state["observations"], evaluation]
    report = Report(
        passed=result.success,
        title=state["report"].title or "browser-use 自动化测试报告",
        markdown=_render_browser_use_report({**state, "evaluation": evaluation, "observations": observations}, result),
    )
    debug_print("evaluate_result", evaluation)
    return {**state, "evaluation": evaluation, "observations": observations, "report": report}


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
