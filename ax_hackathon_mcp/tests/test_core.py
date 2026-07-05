from kakaopay_kospi_regime_mcp.core import forecast_close_model, forecast_open_model, score_model


def test_open_relief():
    out = forecast_open_model({
        "prev_close": 7648.09,
        "prev_prev_close": 8303.41,
        "ewy_pct": -2.8,
        "sox_pct": -5.45,
        "negative_news_count": 1,
        "fresh_negative_news": False,
    })
    assert out["regime"] == "post_crash_relief_possible"


def test_close_absorption():
    out = forecast_close_model({
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
    })
    assert out["regime"] == "institution_absorption"


def test_score():
    out = score_model(8525, 8591.5)
    assert out["tier_score"] == 3
