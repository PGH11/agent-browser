"""启动前端 Web 应用。"""

from __future__ import annotations

from pathlib import Path

import uvicorn


if __name__ == "__main__":
    log_file = Path("artifacts/web_app_boot.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        uvicorn.run(
            "test_agent.web_app:app",
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )
    except Exception as exc:
        log_file.write_text(str(exc), encoding="utf-8")
        raise
