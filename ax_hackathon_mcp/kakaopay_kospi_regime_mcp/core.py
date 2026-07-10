from __future__ import annotations

from typing import Any


def f(x: Any, default: float = 0.0) -> float:
    if x in (None, ""):
        return default
    try:
        return float(str(x).replace(",", "").replace("%", "").replace("+", "").strip())
    except Exception:
        return default


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def forecast_open_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    prev = f(snapshot.get("prev_close"), 8088.34)
    prev_prev = f(snapshot.get("prev_prev_close"), prev)
    ewy = f(snapshot.get("ewy_pct"))
    sox = f(snapshot.get("sox_pct"))
    mu = f(snapshot.get("mu_pct"))
    nvda = f(snapshot.get("nvda_pct"))
    meta = f(snapshot.get("meta_pct"))
    usdkrw = f(snapshot.get("usdkrw"), 1360)
    neg_news = int(f(snapshot.get("negative_news_count"), 0))
    fresh_shock = bool(snapshot.get("fresh_negative_news", neg_news >= 3))

    prior_ret = prev / prev_prev - 1 if prev_prev else 0
    semi = 0.45 * sox + 0.25 * mu + 0.20 * nvda + 0.10 * meta
    ewy_gap = clamp(0.58 * ewy / 100, -0.035, 0.035)
    semi_gap = clamp(semi / 240, -0.030, 0.030)
    fx_drag = clamp((usdkrw - 1350) / 10000, -0.004, 0.009)
    post_crash_relief = prior_ret <= -0.05 and ewy > -3.5 and not fresh_shock

    if post_crash_relief:
        open_ret = 0.68 * ewy_gap + 0.22 * semi_gap - 0.45 * fx_drag
        open_ret = max(open_ret, -0.015)
        regime = "post_crash_relief_possible"
    elif fresh_shock and (semi <= -2.5 or ewy <= -2.5):
        open_ret = 0.45 * ewy_gap + 0.45 * semi_gap - 0.75 * fx_drag - 0.006
        regime = "shock_gap_down"
    elif ewy >= 1.0 and semi >= 0:
        open_ret = 0.62 * ewy_gap + 0.28 * semi_gap - 0.35 * fx_drag
        regime = "overnight_relief"
    else:
        open_ret = 0.55 * ewy_gap + 0.35 * semi_gap - 0.45 * fx_drag
        regime = "stabilization_watch"

    pred = round(prev * (1 + open_ret))
    width = 70 if abs(open_ret) < 0.012 else 110
    reasons = []
    if ewy < -1:
        reasons.append("EWY drag")
    elif ewy > 1:
        reasons.append("EWY relief")
    if semi < -1:
        reasons.append("semi voltage weak")
    elif semi > 1:
        reasons.append("semi voltage positive")
    if post_crash_relief:
        reasons.append("prior crash exhaustion")
    if fresh_shock:
        reasons.append("fresh negative news")
    if usdkrw > 1380:
        reasons.append("FX resistance")
    if not reasons:
        reasons.append("mixed signals")

    confidence = clamp(0.55 + 0.05 * (abs(ewy) > 1) + 0.04 * (abs(semi) > 1) - 0.05 * fresh_shock, 0.35, 0.72)
    return {
        "forecast_open": pred,
        "range": [round(pred - width), round(pred + width)],
        "regime": regime,
        "confidence": round(confidence, 2),
        "inputs": {
            "prev_close": prev,
            "prior_return": round(prior_ret, 4),
            "ewy_pct": ewy,
            "semi_impulse": round(semi, 3),
            "fx_drag": round(fx_drag, 4),
            "fresh_negative_news": fresh_shock,
        },
        "reason": reasons,
        "disclaimer": "Research and information only. Not investment advice.",
    }


def forecast_close_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    current = f(snapshot.get("current"), f(snapshot.get("close"), 8000))
    open_ = f(snapshot.get("open"), current)
    high = f(snapshot.get("high"), max(current, open_))
    low = f(snapshot.get("low"), min(current, open_))
    prev = f(snapshot.get("prev_close"), current)
    foreign = f(snapshot.get("foreign"))
    inst = f(snapshot.get("institution"))
    program = f(snapshot.get("program"))
    rise = f(snapshot.get("rise_count"))
    fall = f(snapshot.get("fall_count"))
    trading_value_accel = bool(snapshot.get("trading_value_acceleration", False))

    breadth = (rise - fall) / max(rise + fall, 1)
    gap_fail = max(open_ - current, 0)
    low_recovery = max(current - low, 0)
    flow = 0.000004 * inst + 0.000003 * foreign + 0.000004 * program
    inst_absorption = inst >= 30000 and breadth >= 0.20 and current > open_ and current >= (high + low) / 2
    avalanche = foreign <= -30000 and program <= -20000 and not inst_absorption

    raw = current - 0.35 * gap_fail + 0.20 * low_recovery + flow + 45 * breadth
    if inst_absorption:
        raw += 0.35 * max(high - current, 0) + 70
    if trading_value_accel and inst_absorption:
        raw += 35
    if avalanche:
        raw -= 0.25 * low_recovery + 90

    if avalanche:
        regime = "avalanche_sell"
        width = 130
    elif inst_absorption:
        regime = "institution_absorption"
        width = 90
    elif current < prev * 0.97:
        regime = "panic_continuation"
        width = 140
    else:
        regime = "range_close"
        width = 80

    pred = round(raw)
    return {
        "forecast_close": pred,
        "range": [round(pred - width), round(pred + width)],
        "regime": regime,
        "confidence": round(clamp(0.52 + 0.08 * inst_absorption + 0.06 * avalanche, 0.35, 0.72), 2),
        "flags": {
            "institution_absorption": inst_absorption,
            "avalanche_sell": avalanche,
            "trading_value_acceleration": trading_value_accel,
        },
        "inputs": {
            "current": current,
            "foreign": foreign,
            "institution": inst,
            "program": program,
            "breadth": round(breadth, 3),
        },
        "reason": close_reasons(inst_absorption, avalanche, breadth, trading_value_accel),
        "disclaimer": "Research and information only. Not investment advice.",
    }


def close_reasons(inst_absorption: bool, avalanche: bool, breadth: float, trading_value_accel: bool) -> list[str]:
    out = []
    if avalanche:
        out.append("foreign and program selling crossed avalanche threshold")
    if inst_absorption:
        out.append("institution buying absorbed supply")
    if breadth > 0.2:
        out.append("market breadth positive")
    elif breadth < -0.2:
        out.append("market breadth weak")
    if trading_value_accel:
        out.append("trading value acceleration detected")
    return out or ["mixed intraday flow"]


def explain_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    ewy = f(snapshot.get("ewy_pct"))
    sox = f(snapshot.get("sox_pct"))
    foreign = f(snapshot.get("foreign"))
    inst = f(snapshot.get("institution"))
    program = f(snapshot.get("program"))
    neg_news = int(f(snapshot.get("negative_news_count"), 0))
    return {
        "circuit": {
            "T_EWY": "positive" if ewy > 0 else "negative" if ewy < 0 else "neutral",
            "V_semi": "positive" if sox > 0 else "negative" if sox < 0 else "neutral",
            "D_avalanche": foreign <= -30000 and program <= -20000,
            "C_absorption": inst >= 30000,
            "S_news": "risk_on" if neg_news >= 3 else "normal",
        },
        "plain_korean": [
            "EWY는 미국 시간의 한국 가격발견 신호입니다.",
            "반도체 전압은 SOX/MU/NVDA/META로 분리해 봅니다.",
            "외국인·프로그램 매도가 임계값을 넘으면 하방 다이오드가 켜집니다.",
            "기관 매수가 충분히 크면 매도 충격을 흡수하는 커패시터로 봅니다.",
        ],
    }


def score_model(predicted: float, actual: float) -> dict[str, Any]:
    p = f(predicted)
    a = f(actual)
    err = abs(p - a)
    pct = err / a if a else 0
    if pct <= 0.005:
        tier = 5
    elif pct <= 0.0075:
        tier = 4
    elif pct <= 0.010:
        tier = 3
    elif pct <= 0.015:
        tier = 2
    elif pct <= 0.020:
        tier = 1
    else:
        tier = 0
    return {"predicted": p, "actual": a, "error_points": round(err, 2), "error_pct": round(pct * 100, 3), "tier_score": tier}


def daily_workflow_model() -> dict[str, Any]:
    return {
        "purpose": "Explainable KOSPI daily regime monitoring workflow",
        "messenger_integration": {
            "kakaopay_securities": "app push, KakaoTalk channel, internal research bot",
            "prototype": "Telegram was used during model validation; production can replace it with KakaoTalk or app notifications",
        },
        "schedule_kst": [
            {
                "time": "07:30",
                "step": "open_forecast",
                "tool": "forecast_open",
                "message": "장전 시가 레짐, 예상 범위, 핵심 근거 발송",
            },
            {
                "time": "09:05",
                "step": "open_score_and_first_monitor",
                "tool": "forecast_close",
                "message": "시가 채점, 갭 성공/실패, 초기 수급 레짐 발송",
            },
            {
                "time": "10:30",
                "step": "second_monitor",
                "tool": "forecast_close",
                "message": "외국인/기관/프로그램 변화와 종가 예비 레짐 발송",
            },
            {
                "time": "12:30",
                "step": "final_close_forecast",
                "tool": "forecast_close",
                "message": "종가 예측 고정, confidence, 리스크 플래그 발송",
            },
            {
                "time": "15:40",
                "step": "score_and_postmortem",
                "tool": "score_prediction",
                "message": "실측 대비 오차, 점수, 틀린 원인, 다음 모델 수정 방향 발송",
            },
        ],
        "design_choice": "The MCP exposes the workflow and message payloads, while scheduling and KakaoTalk delivery should be handled by the host application.",
        "disclaimer": "Research and information only. Not investment advice.",
    }

