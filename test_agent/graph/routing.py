"""条件边路由函数。"""

from __future__ import annotations

from typing import Literal

from test_agent.models import TestAgentState


def route_after_router(state: TestAgentState) -> Literal["validate", "browser_use", "reject"]:
    return state["route"]
