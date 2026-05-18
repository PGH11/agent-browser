"""编译 browser-use 主控状态机。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from test_agent.graph.nodes import (
    analyze_goal,
    evaluate_result,
    plan_browser_action,
    reject_request,
    route_request,
    run_browser_use_agent,
    write_report,
)
from test_agent.graph.routing import route_after_router
from test_agent.models import TestAgentState


def build_graph():
    """构建以 browser-use 为核心执行引擎的 LangGraph。"""

    graph = StateGraph(TestAgentState)
    graph.add_node("route_request", route_request)
    graph.add_node("analyze_goal", analyze_goal)
    graph.add_node("plan_browser_action", plan_browser_action)
    graph.add_node("browser_use", run_browser_use_agent)
    graph.add_node("evaluate_result", evaluate_result)
    graph.add_node("reject_request", reject_request)
    graph.add_node("write_report", write_report)

    graph.add_edge(START, "route_request")
    graph.add_conditional_edges(
        "route_request",
        route_after_router,
        {
            "browser_use": "analyze_goal",
            "reject": "reject_request",
        },
    )
    graph.add_edge("analyze_goal", "plan_browser_action")
    graph.add_edge("plan_browser_action", "browser_use")
    graph.add_edge("browser_use", "evaluate_result")
    graph.add_edge("evaluate_result", "write_report")
    graph.add_edge("reject_request", "write_report")
    graph.add_edge("write_report", END)

    return graph.compile()
