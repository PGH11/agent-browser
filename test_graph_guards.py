from test_agent.graph import nodes
from test_agent.graph.nodes import _evaluate_browser_use_result, route_request, validate_request
from test_agent.models import BrowserUseResult, PageSnapshot, Report, TestRequest as AgentTestRequest


def _state(goal: str) -> dict:
    return {
        "request": AgentTestRequest(base_url="https://example.com/", goal=goal),
        "route": "browser_use",
        "route_reason": "",
        "task_type": "",
        "test_plan": [],
        "assertions": [],
        "browser_instruction": "",
        "memories": [],
        "page_snapshot": PageSnapshot(),
        "observations": [],
        "evaluation": "",
        "browser_use_result": BrowserUseResult(),
        "report": Report(passed=False, title="", markdown=""),
        "errors": [],
    }


def test_route_request_sends_complete_request_to_ai_validation() -> None:
    state = route_request(_state("666"))

    assert state["route"] == "validate"
    assert "AI 请求合理性判断" in state["route_reason"]


def test_route_request_accepts_action_goal() -> None:
    state = route_request(_state("测试登录功能是否正常"))

    assert state["route"] == "validate"


def test_validate_request_rejects_meaningless_goal(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "validate_request_with_ai",
        lambda request: {
            "is_valid": False,
            "reason": "测试目标过于模糊。",
            "normalized_goal": request.goal,
        },
    )

    state = validate_request(_state("666"))

    assert state["route"] == "reject"
    assert "测试目标过于模糊" in state["route_reason"]


def test_evaluate_rejects_wait_only_success() -> None:
    result = BrowserUseResult(success=True, final_result="Waited for 10 seconds", urls=["https://example.com/"], steps=7)

    passed, evaluation, errors = _evaluate_browser_use_result(_state("测试按钮是否正常"), result)

    assert passed is False
    assert "只执行了等待" in evaluation
    assert errors


def test_evaluate_rejects_about_blank_final_url() -> None:
    result = BrowserUseResult(success=True, final_result="任务完成", urls=["https://example.com/", "about:blank"], steps=7)

    passed, evaluation, errors = _evaluate_browser_use_result(_state("测试按钮是否正常"), result)

    assert passed is False
    assert "about:blank" in evaluation
    assert errors


def test_evaluate_uses_ai_for_positive_result_with_negated_error_words(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "evaluate_result_with_ai",
        lambda request, snapshot, task_type, test_plan, assertions, result: {
            "passed": True,
            "confidence": "high",
            "reason": "browser-use 最终报告逐条满足断言，否定语义中的错误词不是失败。",
            "failed_assertions": [],
            "uncertain_points": [],
        },
    )
    result = BrowserUseResult(
        success=True,
        final_result=(
            "### 断言验证结果\n"
            "**断言1：所有按钮均处于可交互状态**\n"
            "- ✅ 通过：共找到3个按钮，全部点击时均有响应。\n"
            "**断言2：跳转后页面无阻断性错误、无加载失败异常**\n"
            "- ✅ 通过：所有3个订单页面均成功加载，未出现4xx/5xx HTTP错误。\n"
            "### 最终结论\n"
            "本次购买按钮功能测试全部通过，所有3个按钮功能均正常。"
        ),
        urls=["https://example.com/", "https://order.example.com/cart-pro"],
        steps=8,
    )

    passed, evaluation, errors = _evaluate_browser_use_result(_state("测试购买按钮是否正常"), result)

    assert passed is True
    assert "AI 外层评估为通过" in evaluation
    assert errors == []


def test_evaluate_uses_ai_for_negative_result(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "evaluate_result_with_ai",
        lambda request, snapshot, task_type, test_plan, assertions, result: {
            "passed": False,
            "confidence": "medium",
            "reason": "报告没有提供满足关键断言的证据。",
            "failed_assertions": ["缺少跳转后的页面标题证据"],
            "uncertain_points": ["无法确认目标按钮是否被点击"],
        },
    )
    result = BrowserUseResult(
        success=True,
        final_result="测试已执行，但没有说明页面跳转后的标题或状态。",
        urls=["https://example.com/"],
        steps=5,
    )

    passed, evaluation, errors = _evaluate_browser_use_result(_state("测试按钮跳转是否正常"), result)

    assert passed is False
    assert "AI 外层评估为失败" in evaluation
    assert "缺少跳转后的页面标题证据" in evaluation
    assert errors == []
