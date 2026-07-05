import json

from kakaopay_kospi_regime_mcp.core import daily_workflow_model, explain_model, forecast_close_model, forecast_open_model, score_model


open_input = {
    "prev_close": 8088.34,
    "prev_prev_close": 7648.09,
    "ewy_pct": -1.2,
    "sox_pct": -0.8,
    "mu_pct": -1.5,
    "nvda_pct": -0.6,
    "meta_pct": 0.2,
    "usdkrw": 1368,
    "negative_news_count": 1,
}

close_input = {
    "current": 7953.86,
    "open": 7933.10,
    "high": 8136.28,
    "low": 7723.57,
    "prev_close": 7648.09,
    "foreign": -22123,
    "institution": 44451,
    "program": -12000,
    "rise_count": 589,
    "fall_count": 297,
    "trading_value_acceleration": True,
}

print(json.dumps({
    "forecast_open": forecast_open_model(open_input),
    "forecast_close": forecast_close_model(close_input),
    "explain_regime": explain_model(close_input),
    "score_prediction": score_model(8525, 8591.5),
    "daily_workflow": daily_workflow_model(),
}, ensure_ascii=False, indent=2))

