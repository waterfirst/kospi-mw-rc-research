from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "krx_actor_verification_pipeline" / "outputs_predictive_extension"
DEPS = ROOT / ".deps" / "finance-datareader"

if DEPS.exists():
    sys.path.insert(0, str(DEPS))

KOSPI_TROUGH = 8203.84
KOSPI_TARGET = 9000.0
KOSPI_PREV_HIGH = 9114.55


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


def get_fdr():
    try:
        import FinanceDataReader as fdr  # type: ignore

        return fdr
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"FinanceDataReader import failed: {exc}") from exc


def latest_ohlc(symbol: str, start: str = "2026-06-23") -> dict:
    fdr = get_fdr()
    df = fdr.DataReader(symbol, start)
    if df is None or len(df) == 0:
        raise RuntimeError(f"No data returned for {symbol}")
    row = df.iloc[-1]
    idx = df.index[-1]
    close = float(row["Close"])
    high = float(row["High"]) if "High" in df.columns else close
    low = float(row["Low"]) if "Low" in df.columns else close
    open_ = float(row["Open"]) if "Open" in df.columns else close
    if "Change" in df.columns:
        change = float(row["Change"])
    elif len(df) >= 2:
        prev = float(df.iloc[-2]["Close"])
        change = close / prev - 1.0
    else:
        change = 0.0
    return {
        "symbol": symbol,
        "date": str(getattr(idx, "date", lambda: idx)()),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "change": change,
    }


def latest_change(symbol: str, start: str = "2026-06-23") -> dict:
    data = latest_ohlc(symbol, start)
    return {
        "symbol": data["symbol"],
        "date": data["date"],
        "close": data["close"],
        "change": data["change"],
    }


def safe_latest(symbol: str, label: str, *, ohlc: bool = False) -> dict:
    try:
        data = latest_ohlc(symbol) if ohlc else latest_change(symbol)
        data["label"] = label
        data["ok"] = True
        return data
    except Exception as exc:
        return {"symbol": symbol, "label": label, "ok": False, "error": str(exc)}


def pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def fmt_price(x: float) -> str:
    return f"{x:,.2f}"


def ch(item: dict, default: float = 0.0) -> float:
    return float(item.get("change", default)) if item.get("ok") else default


def recovery_metrics(kospi: dict) -> dict:
    close = float(kospi.get("close", 8930.30))
    high = float(kospi.get("high", close))
    recovery_to_9000 = (close - KOSPI_TROUGH) / (KOSPI_TARGET - KOSPI_TROUGH)
    high_recovery_to_9000 = (high - KOSPI_TROUGH) / (KOSPI_TARGET - KOSPI_TROUGH)
    recovery_to_prev_high = (close - KOSPI_TROUGH) / (KOSPI_PREV_HIGH - KOSPI_TROUGH)
    return {
        "close": close,
        "high": high,
        "recovery_to_9000": recovery_to_9000,
        "high_recovery_to_9000": high_recovery_to_9000,
        "recovery_to_prev_high": recovery_to_prev_high,
        "touched_9000": high >= KOSPI_TARGET,
        "closed_above_8900": close >= 8900,
        "closed_above_9000": close >= KOSPI_TARGET,
    }


def build_decision(items: dict[str, dict]) -> tuple[str, list[str]]:
    kospi = items.get("KS11", {})
    qqq = items.get("QQQ", {})
    soxx = items.get("SOXX", {})
    smh = items.get("SMH", {})
    ewy = items.get("EWY", {})
    mu = items.get("MU", {})
    nvda = items.get("NVDA", {})

    metrics = recovery_metrics(kospi)
    qqq_ch = ch(qqq)
    soxx_ch = ch(soxx)
    smh_ch = ch(smh)
    ewy_ch = ch(ewy)
    mu_ch = ch(mu)
    nvda_ch = ch(nvda)

    semi_stress = min(soxx_ch, smh_ch, mu_ch, nvda_ch)
    us_ok = ewy_ch >= 0 and qqq_ch > -0.008 and semi_stress > -0.015
    semi_ok = soxx_ch >= 0 or smh_ch >= 0 or (mu_ch >= 0 and nvda_ch >= 0)

    reasons: list[str] = []
    if metrics["closed_above_9000"] and us_ok:
        reasons.append("9,000 종가 회복 + 미국 피드백 중립 이상")
        return "강공: KODEX200 900만원, 반도체 300만원까지 허용", reasons
    if metrics["closed_above_8900"] and metrics["touched_9000"] and us_ok:
        reasons.append("Fast-V 가격 회복 90% 이상, 9,000 장중 통과")
        if semi_ok:
            return "공격 1차: KODEX200 700~900만원 + 반도체 150~300만원", reasons
        return "공격 1차: KODEX200 500~800만원, 반도체는 보류", reasons
    if metrics["closed_above_8900"] and semi_stress > -0.02:
        reasons.append("8,900 종가권 방어, 미국 반도체 급락 없음")
        return "조건부 집행: KODEX200 400~600만원", reasons
    if float(kospi.get("close", 0.0)) >= 8700 and ewy_ch > -0.015:
        reasons.append("가격 회복은 살아 있으나 8,900 안착 전")
        return "탐색 집행: KODEX200 300~500만원", reasons

    reasons.append("가격 Fast-V 훼손 또는 미국 피드백 악화")
    return "대기: 8,800 회복 전 신규 집행 보류", reasons


def build_six_hour_forecast(items: dict[str, dict]) -> str:
    kospi = items.get("KS11", {})
    qqq = items.get("QQQ", {})
    soxx = items.get("SOXX", {})
    smh = items.get("SMH", {})
    ewy = items.get("EWY", {})
    mu = items.get("MU", {})
    nvda = items.get("NVDA", {})

    metrics = recovery_metrics(kospi)
    semi_stress = min(ch(soxx), ch(smh), ch(mu), ch(nvda))
    ewy_ch = ch(ewy)
    qqq_ch = ch(qqq)

    if metrics["closed_above_9000"] and ewy_ch >= 0 and semi_stress > -0.012:
        return "9,000 위 안착 시도, 다음 저항 9,050~9,150"
    if metrics["closed_above_8900"] and metrics["touched_9000"] and semi_stress > -0.015:
        return "8,900 방어 후 9,000 종가 재도전 우세"
    if metrics["closed_above_8900"] and (semi_stress <= -0.015 or qqq_ch <= -0.012):
        return "9,000 터치 후 8,800~8,900 흔들림 경계"
    if float(kospi.get("close", 0.0)) >= 8700 and ewy_ch > -0.015:
        return "8,800 재회복 시도, 실패하면 Fast-V 둔화"
    return "8,650~8,800 재시험 가능, 신규 진입 속도 낮춤"


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram credentials are missing. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = Request(url, data=payload, method="POST")
    with urlopen(request, timeout=20) as response:
        body = response.read(300).decode("utf-8", errors="replace")
        if response.status != 200:
            raise RuntimeError(f"Telegram send failed: {response.status} {body}")


def main() -> None:
    load_env(ROOT / ".env")
    dry_run = "--dry-run" in sys.argv or os.getenv("DRY_RUN") == "1"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    symbols = {
        "KS11": ("KOSPI", True),
        "QQQ": ("Nasdaq100 ETF", False),
        "SOXX": ("SOX proxy SOXX", False),
        "SMH": ("Semiconductor ETF SMH", False),
        "EWY": ("Korea ETF EWY", False),
        "MU": ("Micron", False),
        "NVDA": ("Nvidia", False),
        "AMD": ("AMD", False),
        "INTC": ("Intel", False),
    }
    results = {symbol: safe_latest(symbol, label, ohlc=ohlc) for symbol, (label, ohlc) in symbols.items()}
    decision, reasons = build_decision(results)
    kospi = results.get("KS11", {})
    metrics = recovery_metrics(kospi)

    def line(symbol: str) -> str:
        item = results.get(symbol, {})
        if item.get("ok"):
            return f"{symbol} {pct(float(item['change']))}"
        return f"{symbol} N/A"

    if kospi.get("ok"):
        kospi_line = (
            f"KOSPI {fmt_price(float(kospi['close']))}({pct(float(kospi['change']))}) "
            f"/ 고가 {fmt_price(float(kospi['high']))}"
        )
    else:
        kospi_line = "KOSPI N/A / 전일 기준 Fast-V 추적"

    lines = [
        "[Codex 08:00 KOSPI RC-v7]",
        kospi_line,
        f"회복: 9000 대비 {metrics['recovery_to_9000'] * 100:.0f}% / 실현 τ 0.8~1.77일 / 외국인 대기 폐기",
        f"미국: {line('QQQ')} / {line('SOXX')} / {line('SMH')} / {line('EWY')}",
        f"칩: {line('MU')} / {line('NVDA')} / {line('AMD')} / {line('INTC')}",
        f"6시간 전망: {build_six_hour_forecast(results)}",
        f"판정: {decision}",
        "중지: 8,800 이탈 또는 SOXX/SMH -1.5% 이하",
        "외국인: 진입조건 아님, 9,000 안착 후 보유 지속성만 검증",
    ]
    if reasons:
        lines.append(f"근거: {reasons[0]}")
    lines.append("연구용 판단. 최종 매수는 본인 결정.")
    message = "\n".join(lines)

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (OUT / f"telegram_us_monitor_{stamp}.json").write_text(
        json.dumps(
            {
                "time": now,
                "model_version": "v7_rc_parallel_sigma_total",
                "results": results,
                "metrics": metrics,
                "decision": decision,
                "reasons": reasons,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / f"telegram_us_monitor_{stamp}.txt").write_text(message, encoding="utf-8")
    if dry_run:
        print(message)
    else:
        send_telegram(message)


if __name__ == "__main__":
    main()
