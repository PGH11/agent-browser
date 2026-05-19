"""AI 驱动的请求校验、测试计划和断言生成。"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # 允许在只跑本地单元测试时没有安装 openai。
    OpenAI = None

from test_agent.models import BrowserUseResult, PageSnapshot, TestRequest
from test_agent.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def validate_request_with_ai(request: TestRequest) -> dict[str, Any]:
    """用模型判断 URL 和测试目标是否构成可执行的浏览器测试请求。"""

    fallback = _fallback_validate_request(request)
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback

    prompt = (
        "你是自动化测试 Agent 的请求路由器。请判断用户输入的 URL 和测试目标是否足够明确，"
        "是否值得启动浏览器执行。\n\n"
        "判定规则：\n"
        "1. URL 必须像 http/https 页面地址。\n"
        "2. 测试目标必须描述可执行或可验证的浏览器行为，例如点击、输入、提交、跳转、检查页面状态、验证某功能。\n"
        "3. 纯数字、随意字符、问候语、无页面动作的问题、只有“看看”“试试”但没有目标的输入，都应拒绝。\n"
        "4. 不要根据历史记忆猜测用户想测什么，只根据本次 URL 和测试目标判断。\n\n"
        "请只返回 JSON：\n"
        "{\n"
        '  "is_valid": true 或 false,\n'
        '  "reason": "中文原因",\n'
        '  "normalized_goal": "保留用户真实意图的简短目标，不要补充用户没说的范围"\n'
        "}\n\n"
        f"URL: {request.base_url}\n"
        f"测试目标: {request.goal}\n"
    )
    data = _chat_json(prompt, fallback=fallback)
    return {
        "is_valid": bool(data.get("is_valid", fallback["is_valid"])),
        "reason": str(data.get("reason") or fallback["reason"]).strip(),
        "normalized_goal": str(data.get("normalized_goal") or request.goal).strip(),
    }


def generate_plan_with_ai(request: TestRequest, snapshot: PageSnapshot, memories: list[str]) -> dict[str, Any]:
    """基于用户目标和页面快照生成动态测试计划。"""

    fallback = {
        "task_type": "页面行为测试",
        "test_plan": [
            "打开目标页面并观察当前页面状态。",
            "根据用户测试目标定位相关页面区域或元素。",
            "执行与测试目标直接相关的浏览器操作。",
            "基于 URL、标题、可见文本、元素状态或截图变化判断结果。",
        ],
    }
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback

    prompt = (
        "你是自动化测试 Agent 的测试计划生成器。请根据用户测试目标和页面快照，生成本次测试的动态计划。\n\n"
        "重要原则：\n"
        "1. 不要使用固定模板，不要因为页面里有 footer/nav/login 就自动测试它们。\n"
        "2. 计划必须只围绕用户本次明确提出的目标。\n"
        "3. 如果用户没有要求全量巡检，不要扩大范围。\n"
        "4. 如果页面快照没有找到目标元素，也要给出合理的探索步骤，而不是假设元素存在。\n"
        "5. 每一步都要是 browser-use 可以执行或观察的浏览器动作。\n\n"
        "请只返回 JSON：\n"
        "{\n"
        '  "task_type": "简短任务类型",\n'
        '  "test_plan": ["步骤1", "步骤2", "步骤3"]\n'
        "}\n\n"
        f"目标 URL: {request.base_url}\n"
        f"用户测试目标: {request.goal}\n\n"
        f"页面快照摘要:\n{snapshot.summary or '无可用页面快照'}\n\n"
        f"同域名历史记忆，仅可作为避坑参考，不能改变本次测试范围:\n{_format_memories(memories)}\n"
    )
    data = _chat_json(prompt, fallback=fallback)
    plan = data.get("test_plan") if isinstance(data.get("test_plan"), list) else fallback["test_plan"]
    clean_plan = [str(item).strip() for item in plan if str(item).strip()]
    return {
        "task_type": str(data.get("task_type") or fallback["task_type"]).strip(),
        "test_plan": clean_plan or fallback["test_plan"],
    }


def generate_assertions_with_ai(request: TestRequest, snapshot: PageSnapshot, task_type: str, test_plan: list[str]) -> list[str]:
    """基于动态计划生成外层断言。"""

    fallback = [
        "页面操作过程中不能出现 404、Not Found、Error、空白页或明显加载失败。",
        "最终报告必须记录实际 URL、页面标题或关键可见文本作为验证依据。",
        "如果无法确认结果，应输出“不确定”并说明缺少哪类证据，而不是直接判定通过。",
    ]
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback

    prompt = (
        "你是自动化测试 Agent 的断言生成器。请根据用户目标、页面快照和测试计划，生成本次测试需要验证的断言。\n\n"
        "要求：\n"
        "1. 断言必须服务于用户本次目标，不要扩展到用户没要求的区域。\n"
        "2. 断言要可观察，例如 URL、标题、文本、按钮状态、弹窗状态、错误提示、截图变化。\n"
        "3. 必须包含失败/不确定时的判断依据。\n"
        "4. 不要写固定场景模板。\n\n"
        "请只返回 JSON：\n"
        "{\n"
        '  "assertions": ["断言1", "断言2", "断言3"]\n'
        "}\n\n"
        f"任务类型: {task_type}\n"
        f"用户测试目标: {request.goal}\n"
        f"测试计划:\n{_numbered(test_plan)}\n\n"
        f"页面快照摘要:\n{snapshot.summary or '无可用页面快照'}\n"
    )
    data = _chat_json(prompt, fallback={"assertions": fallback})
    assertions = data.get("assertions") if isinstance(data.get("assertions"), list) else fallback
    clean_assertions = [str(item).strip() for item in assertions if str(item).strip()]
    return clean_assertions or fallback


def evaluate_result_with_ai(
    request: TestRequest,
    snapshot: PageSnapshot,
    task_type: str,
    test_plan: list[str],
    assertions: list[str],
    result: BrowserUseResult,
) -> dict[str, Any]:
    """用 AI 判断 browser-use 最终结果是否满足本次测试目标和断言。"""

    fallback = {
        "passed": bool(result.success and result.final_result.strip()),
        "confidence": "low",
        "reason": "AI 评估不可用，使用 browser-use success 与最终结果是否存在作为保守兜底。",
        "failed_assertions": [],
        "uncertain_points": ["AI 评估不可用，建议人工复核最终报告。"],
    }
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback

    prompt = (
        "你是自动化测试 Agent 的外层评估器。请根据用户原始目标、测试计划、断言和 browser-use 最终报告，"
        "判断本次测试是否真正通过。\n\n"
        "评估原则：\n"
        "1. 只评估用户本次目标和外层断言，不要扩大范围。\n"
        "2. 重点判断 browser-use 的最终报告是否提供了足够证据满足断言。\n"
        "3. 中文里的“无错误”“未出现错误”“无加载失败”表示没有错误，不能因为包含“错误/失败”二字就判失败。\n"
        "4. 如果报告自相矛盾、证据不足、没有逐条验证关键断言，应判为不通过或低置信度。\n"
        "5. 如果 browser-use success 为 false，应倾向不通过，除非最终报告有非常明确的反向证据。\n\n"
        "请只返回 JSON：\n"
        "{\n"
        '  "passed": true 或 false,\n'
        '  "confidence": "high|medium|low",\n'
        '  "reason": "中文评估原因",\n'
        '  "failed_assertions": ["未满足的断言"],\n'
        '  "uncertain_points": ["证据不足或需要人工复核的点"]\n'
        "}\n\n"
        f"用户原始目标:\n{request.goal}\n\n"
        f"任务类型:\n{task_type or '未分类'}\n\n"
        f"测试计划:\n{_numbered(test_plan) or '无'}\n\n"
        f"外层断言:\n{_numbered(assertions) or '无'}\n\n"
        f"页面快照摘要:\n{snapshot.summary or '无可用页面快照'}\n\n"
        f"browser-use success: {result.success}\n"
        f"browser-use 执行步数: {result.steps}\n"
        f"访问过的 URL:\n{_numbered(result.urls) or '无'}\n\n"
        f"browser-use 错误列表:\n{_numbered(result.errors) or '无'}\n\n"
        f"browser-use 最终报告:\n{result.final_result or '无'}\n"
    )
    data = _chat_json(prompt, fallback=fallback)
    failed_assertions = data.get("failed_assertions") if isinstance(data.get("failed_assertions"), list) else []
    uncertain_points = data.get("uncertain_points") if isinstance(data.get("uncertain_points"), list) else []
    return {
        "passed": bool(data.get("passed", fallback["passed"])),
        "confidence": str(data.get("confidence") or fallback["confidence"]).strip(),
        "reason": str(data.get("reason") or fallback["reason"]).strip(),
        "failed_assertions": [str(item).strip() for item in failed_assertions if str(item).strip()],
        "uncertain_points": [str(item).strip() for item in uncertain_points if str(item).strip()],
    }


def _chat_json(prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你只输出合法 JSON，不输出 Markdown，不输出解释。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return _parse_json(content, fallback)
    except Exception:
        return fallback


def _parse_json(content: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else fallback
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            return fallback
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else fallback
        except json.JSONDecodeError:
            return fallback


def _fallback_validate_request(request: TestRequest) -> dict[str, Any]:
    url = request.base_url.strip().lower()
    goal = request.goal.strip()
    normalized = re.sub(r"[\W_]+", "", goal.lower(), flags=re.UNICODE)
    is_valid_url = url.startswith(("http://", "https://"))
    action_words = [
        "测试",
        "检查",
        "验证",
        "打开",
        "点击",
        "输入",
        "提交",
        "跳转",
        "进入",
        "是否",
        "正常",
        "test",
        "check",
        "verify",
        "click",
        "input",
        "submit",
        "open",
    ]
    is_meaningful_goal = (
        bool(normalized)
        and not normalized.isdigit()
        and len(normalized) >= 2
        and any(word in goal.lower() for word in action_words)
    )
    return {
        "is_valid": is_valid_url and is_meaningful_goal,
        "reason": "请求具备基础 URL 和测试目标。" if is_valid_url and is_meaningful_goal else "URL 或测试目标不具备可执行性。",
        "normalized_goal": goal,
    }


def _format_memories(memories: list[str]) -> str:
    return "\n".join(f"- {item}" for item in memories[:5]) if memories else "- 暂无"


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))
