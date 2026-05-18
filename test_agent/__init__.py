"""Playwright automation test agent package."""

__all__ = ["build_graph", "run_cli"]


def __getattr__(name: str):
    if name == "build_graph":
        from test_agent.graph.builder import build_graph

        return build_graph
    if name == "run_cli":
        from test_agent.cli import run_cli

        return run_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
