"""调试日志辅助函数。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from test_agent.settings import DEBUG_AI_OUTPUT


def debug_print(title: str, payload: Any) -> None:
    """当 DEBUG_AI_OUTPUT=1 时打印结构化调试输出。"""

    if not DEBUG_AI_OUTPUT:
        return

    if isinstance(payload, BaseModel):
        text = payload.model_dump_json(indent=2)
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    print(f"\n[DEBUG] {title}:\n{text}\n")
