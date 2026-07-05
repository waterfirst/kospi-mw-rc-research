from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import explain_model, forecast_close_model, forecast_open_model, score_model
from .submission import ANSWERS


mcp = FastMCP("kakaopay-kospi-regime")


@mcp.tool()
def forecast_open(snapshot: dict[str, Any]) -> dict[str, Any]:
    return forecast_open_model(snapshot or {})


@mcp.tool()
def forecast_close(snapshot: dict[str, Any]) -> dict[str, Any]:
    return forecast_close_model(snapshot or {})


@mcp.tool()
def explain_regime(snapshot: dict[str, Any]) -> dict[str, Any]:
    return explain_model(snapshot or {})


@mcp.tool()
def score_prediction(predicted: float, actual: float) -> dict[str, Any]:
    return score_model(predicted, actual)


@mcp.tool()
def submission_answers() -> dict[str, str]:
    return ANSWERS


if __name__ == "__main__":
    mcp.run()

