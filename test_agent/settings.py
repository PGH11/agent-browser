"""项目配置与文件系统路径。"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # 测试覆盖可忽略：python-dotenv 是可选依赖。
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = Path(os.getenv("TEST_AGENT_ARTIFACTS_DIR", PROJECT_ROOT / "artifacts"))
BROWSER_USE_DIR = ARTIFACTS_DIR / "browser_use"
BROWSER_USE_CONFIG_DIR = Path(os.getenv("BROWSER_USE_CONFIG_DIR", BROWSER_USE_DIR / "config"))
BROWSER_USE_PROFILES_DIR = Path(os.getenv("BROWSER_USE_PROFILES_DIR", BROWSER_USE_DIR / "profiles"))
BROWSER_USE_DOWNLOADS_DIR = Path(os.getenv("BROWSER_USE_DOWNLOADS_DIR", BROWSER_USE_DIR / "downloads"))
BROWSER_USE_TRACES_DIR = Path(os.getenv("BROWSER_USE_TRACES_DIR", BROWSER_USE_DIR / "traces"))

os.environ.setdefault("BROWSER_USE_CONFIG_DIR", str(BROWSER_USE_CONFIG_DIR))
os.environ.setdefault("BROWSER_USE_PROFILES_DIR", str(BROWSER_USE_PROFILES_DIR))
os.environ.setdefault("BROWSER_USE_DOWNLOADS_DIR", str(BROWSER_USE_DOWNLOADS_DIR))
os.environ.setdefault("BROWSER_USE_TRACES_DIR", str(BROWSER_USE_TRACES_DIR))

DEFAULT_TIMEOUT_MS = int(os.getenv("TEST_AGENT_TIMEOUT_MS", "10000"))
DEFAULT_BROWSER = os.getenv("TEST_AGENT_BROWSER", "chromium")
DEBUG_AI_OUTPUT = os.getenv("DEBUG_AI_OUTPUT", "0") != "0"
BROWSER_USE_FORCE_STRUCTURED_OUTPUT = os.getenv("BROWSER_USE_FORCE_STRUCTURED_OUTPUT", "1") != "0"

OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY")
    or os.getenv("ARK_API_KEY")
    or os.getenv("DEFAULT_ARK_API_KEY", "")
)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv(
    "ARK_BASE_URL",
    "https://api.openai.com/v1",
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("ARK_MODEL", "gpt-4o-mini")

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "playwright-test-agent")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


def configure_langsmith() -> None:
    """在配置了凭证时启用 LangSmith tracing。"""

    if not LANGSMITH_API_KEY:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT


configure_langsmith()
