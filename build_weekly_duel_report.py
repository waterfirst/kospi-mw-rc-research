#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path("/home/waterfirst/kospi-mw-rc-research")
LOG_DIR = ROOT / "contest" / "learning" / "daily_logs"
POSTMORTEM_DIR = ROOT / "contest" / "learning"
INTRADAY_DIR = ROOT / "contest" / "intraday"
DOCS_DIR = ROOT / "docs"
PAGES_BASE = "https://waterfirst.github.io/kospi-mw-rc-research"


def tier_score(pred: float | None, actual: float | None) -> tuple[int | None, float | None, float | None]:
    if pred is None or actual is None:
        return None, None, None
    abs_err = abs(pred - actual)
    err_pct = abs_err / actual * 100.0
    for thr, pt in ((0.25, 5), (0.50, 4), (0.75, 3), (1.0, 2), (1.5, 1)):
        if err_pct <= thr:
            return pt, abs_err, err_pct
    return 0, abs_err, err_pct


def fmt_num(v: float | None, digits: int = 2) -> str:
    return "—" if v is None else f"{v:,.{digits}f}"


def fmt_score(v: int | None) -> str:
    return "N/A" if v is None else str(v)


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def polyline(points: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def latest_week_dates() -> list[str]:
    date_paths = [p for p in LOG_DIR.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    dates = sorted(datetime.strptime(p.stem, "%Y-%m-%d").date() for p in date_paths)
    if not dates:
        raise FileNotFoundError("No daily logs found.")
    latest = dates[-1]
    monday = latest - timedelta(days=latest.weekday())
    expected = [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    existing = {p.stem for p in date_paths}
    if all(d in existing for d in expected):
        return expected
    return [d.strftime("%Y-%m-%d") for d in dates[-5:]]


def line_chart_svg(
    labels: list[str],
    series: list[dict],
    title: str,
    y_label: str,
    width: int = 760,
    height: int = 320,
) -> str:
    margin = {"l": 58, "r": 24, "t": 28, "b": 44}
    plot_w = width - margin["l"] - margin["r"]
    plot_h = height - margin["t"] - margin["b"]

    values = []
    for s in series:
        values.extend(v for v in s["values"] if v is not None)
    ymin = min(values)
    ymax = max(values)
    pad = max((ymax - ymin) * 0.15, 1)
    ymin -= pad
    ymax += pad

    def xy(i: int, v: float) -> tuple[float, float]:
        x = margin["l"] + plot_w * (i / max(len(labels) - 1, 1))
        y = margin["t"] + plot_h * (1 - (v - ymin) / max(ymax - ymin, 1e-9))
        return x, y

    grid = []
    for n in range(5):
        gy = margin["t"] + plot_h * n / 4
        val = ymax - (ymax - ymin) * n / 4
        grid.append((gy, val))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" aria-label="{svg_escape(title)}">',
        '<rect width="100%" height="100%" fill="#fffdfa"/>',
    ]
    for gy, val in grid:
        parts.append(f'<line x1="{margin["l"]}" y1="{gy:.1f}" x2="{width-margin["r"]}" y2="{gy:.1f}" stroke="#eee6d6" />')
        parts.append(f'<text x="10" y="{gy+4:.1f}" fill="#7a8494" font-size="11">{val:,.0f}</text>')
    parts.append(f'<line x1="{margin["l"]}" y1="{margin["t"]}" x2="{margin["l"]}" y2="{height-margin["b"]}" stroke="#d9cfbd"/>')
    parts.append(f'<line x1="{margin["l"]}" y1="{height-margin["b"]}" x2="{width-margin["r"]}" y2="{height-margin["b"]}" stroke="#d9cfbd"/>')
    for idx, label in enumerate(labels):
        x, _ = xy(idx, ymin)
        parts.append(f'<text x="{x:.1f}" y="{height-16}" text-anchor="middle" fill="#7a8494" font-size="11">{svg_escape(label)}</text>')
    for s in series:
        pts = [xy(i, v) for i, v in enumerate(s["values"]) if v is not None]
        parts.append(f'<polyline fill="none" stroke="{s["color"]}" stroke-width="3.5" points="{polyline(pts)}"/>')
        for i, v in enumerate(s["values"]):
            if v is None:
                continue
            x, y = xy(i, v)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{s["color"]}"/>')
    parts.append(f'<text x="{width/2:.1f}" y="18" text-anchor="middle" fill="#22314d" font-size="16" font-weight="700">{svg_escape(title)}</text>')
    parts.append(f'<text x="16" y="20" fill="#8a5b00" font-size="11">{svg_escape(y_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def bar_chart_svg(labels: list[str], rows: list[dict], width: int = 760, height: int = 320) -> str:
    margin = {"l": 58, "r": 24, "t": 28, "b": 44}
    plot_w = width - margin["l"] - margin["r"]
    plot_h = height - margin["t"] - margin["b"]
    max_y = 10

    def y_of(v: float) -> float:
        return margin["t"] + plot_h * (1 - v / max_y)

    group_w = plot_w / max(len(rows), 1)
    bw = min(22, group_w * 0.24)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" aria-label="점수 막대그래프">',
        '<rect width="100%" height="100%" fill="#fffdfa"/>',
    ]
    for n in range(6):
        gy = margin["t"] + plot_h * n / 5
        val = max_y - max_y * n / 5
        parts.append(f'<line x1="{margin["l"]}" y1="{gy:.1f}" x2="{width-margin["r"]}" y2="{gy:.1f}" stroke="#eee6d6" />')
        parts.append(f'<text x="18" y="{gy+4:.1f}" fill="#7a8494" font-size="11">{val:.0f}</text>')
    parts.append(f'<line x1="{margin["l"]}" y1="{margin["t"]}" x2="{margin["l"]}" y2="{height-margin["b"]}" stroke="#d9cfbd"/>')
    parts.append(f'<line x1="{margin["l"]}" y1="{height-margin["b"]}" x2="{width-margin["r"]}" y2="{height-margin["b"]}" stroke="#d9cfbd"/>')
    for i, row in enumerate(rows):
        gx = margin["l"] + group_w * i + group_w / 2
        claude = row["claude_open_score"] or 0
        codex = row["codex_total_score"]
        parts.append(f'<rect x="{gx-bw-2:.1f}" y="{y_of(claude):.1f}" width="{bw:.1f}" height="{height-margin["b"]-y_of(claude):.1f}" fill="#f28b44" rx="4"/>')
        parts.append(f'<rect x="{gx+2:.1f}" y="{y_of(codex):.1f}" width="{bw:.1f}" height="{height-margin["b"]-y_of(codex):.1f}" fill="#4e79ff" rx="4"/>')
        parts.append(f'<text x="{gx:.1f}" y="{height-16}" text-anchor="middle" fill="#7a8494" font-size="11">{svg_escape(labels[i])}</text>')
    parts.append(f'<text x="{width/2:.1f}" y="18" text-anchor="middle" fill="#22314d" font-size="16" font-weight="700">날짜별 점수</text>')
    parts.append("</svg>")
    return "".join(parts)


def summarize_change_note(data: dict, date_str: str) -> str:
    code_change = data.get("code_change") or {}
    why = code_change.get("why")
    if why:
        return why
    path = POSTMORTEM_DIR / f"POSTMORTEM_{date_str.replace('-', '')}.md"
    if not path.exists():
        return "기록 없음"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## (?:소규모 코드 수정|규칙 수정)\n([\s\S]*?)(?:\n## |\Z)", text)
    if m:
        section = " ".join(line.strip("- ").strip() for line in m.group(1).splitlines() if line.strip())
        return section[:220]
    return "기록 있음"


def summarize_engine_status(data: dict) -> str:
    review = data.get("engine_review") or {}
    parts = []
    for key, label in (
        ("open_engine", "시가"),
        ("flow_nowcast", "수급"),
        ("intraday_close_engine", "종가"),
    ):
        status = review.get(key, {}).get("status")
        if status:
            status_ko = {"hit": "적중", "miss": "실패", "partial_hit": "부분적중"}.get(status, status)
            parts.append(f"{label}:{status_ko}")
    return " · ".join(parts) if parts else "판정 기록 없음"


def build_rows(week_dates: list[str]) -> list[dict]:
    rows = []
    for date_str in week_dates:
        path = LOG_DIR / f"{date_str}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        actual_open = data.get("actuals", {}).get("open")
        actual_close = data.get("actuals", {}).get("close")
        codex_open = data.get("predictions", {}).get("open")
        codex_close = data.get("score_details", {}).get("close_1230_final_model", {}).get("forecast")
        # Daily logs are the score ledger.  The intraday artifact is the
        # immutable source for the 12:30 forecast when older log schemas omit
        # score_details.
        intraday_path = INTRADAY_DIR / f"{date_str.replace('-', '')}_1230_final_model_forecast.json"
        if codex_close is None and intraday_path.exists():
            intraday = json.loads(intraday_path.read_text(encoding="utf-8"))
            codex_close = intraday.get("prediction", {}).get("forecast_close")

        codex_open_score = (
            data.get("score_details", {}).get("open", {}).get("tier_score")
            if data.get("score_details") else data.get("scores", {}).get("open")
        )
        codex_close_score = (
            data.get("score_details", {}).get("close_1230_final_model", {}).get("tier_score")
            if data.get("score_details") else data.get("scores", {}).get("close")
        )
        codex_total_score = (codex_open_score or 0) + (codex_close_score or 0)

        claude_open = data.get("comparison", {}).get("claude_style_inferred_open")
        claude_open_score, claude_open_abs, claude_open_pct = tier_score(claude_open, actual_open)

        if claude_open_score is None:
            winner = "Codex 공식 우위"
        elif claude_open_score > (codex_open_score or 0):
            winner = "Claude 시가 우위"
        elif claude_open_score == (codex_open_score or 0):
            winner = "시가 동률 / 종합은 Codex 자료 우세"
        else:
            winner = "Codex 우위"

        rows.append(
            {
                "date": date_str,
                "actual_open": actual_open,
                "actual_close": actual_close,
                "codex_open": codex_open,
                "codex_close": codex_close,
                "codex_open_score": codex_open_score,
                "codex_close_score": codex_close_score,
                "codex_total_score": codex_total_score,
                "claude_open": claude_open,
                "claude_open_score": claude_open_score,
                "claude_open_abs": claude_open_abs,
                "claude_open_pct": claude_open_pct,
                "winner": winner,
                "change_note": summarize_change_note(data, date_str),
                "status_note": summarize_engine_status(data),
                "failure_tags": data.get("failure_tags") or [],
                "next_candidates": data.get("reflection", {}).get("next_candidates") or [],
                "model_version": data.get("model_version") or "unknown",
            }
        )
    return rows


def circuit_svg(rows: list[dict]) -> str:
    bullet_y = 390
    bullets = []
    for row in rows[-3:]:
        short = row["change_note"][:84] + ("…" if len(row["change_note"]) > 84 else "")
        bullets.append(
            f'<text x="52" y="{bullet_y}" fill="#5f6b7a" font-size="14">• {row["date"]}: {svg_escape(short)}</text>'
        )
        bullet_y += 28
    return f"""
<svg viewBox="0 0 900 520" aria-label="모델 변화 회로도">
  <rect width="100%" height="100%" fill="#fffdfa"/>
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#6c7687"/>
    </marker>
  </defs>
  <text x="32" y="38" fill="#22314d" font-size="22" font-weight="700">모델 변화 과정 — 전기회로도 스타일</text>
  <text x="32" y="64" fill="#6b7585" font-size="13">Claude EWY 직결형 → Codex 다중 앵커·보정 소자 누적형</text>

  <rect x="28" y="92" width="250" height="160" rx="18" fill="#eef4ff" stroke="#c9d9ff"/>
  <text x="48" y="124" fill="#22314d" font-size="18" font-weight="700">1) Claude-style baseline</text>
  <circle cx="76" cy="174" r="22" fill="#fff" stroke="#4e79ff" stroke-width="3"/>
  <text x="76" y="179" text-anchor="middle" font-size="12" fill="#22314d" font-weight="700">EWY</text>
  <line x1="98" y1="174" x2="130" y2="174" stroke="#22314d" stroke-width="3"/>
  <polyline points="130,174 142,160 154,188 166,160 178,188 190,160 202,174" fill="none" stroke="#22314d" stroke-width="3"/>
  <text x="166" y="148" text-anchor="middle" font-size="12" fill="#6b7585">R_fx</text>
  <line x1="202" y1="174" x2="246" y2="174" stroke="#22314d" stroke-width="3"/>
  <rect x="142" y="200" width="98" height="34" rx="12" fill="#fff" stroke="#d7d7d7"/>
  <text x="191" y="222" text-anchor="middle" font-size="12" fill="#6b7585">직접 EWY 변환</text>

  <rect x="324" y="92" width="250" height="160" rx="18" fill="#fff2e7" stroke="#ffd5bc"/>
  <text x="344" y="124" fill="#22314d" font-size="18" font-weight="700">2) 중간 보정층</text>
  <circle cx="372" cy="174" r="22" fill="#fff" stroke="#f28b44" stroke-width="3"/>
  <text x="372" y="179" text-anchor="middle" font-size="11" fill="#22314d" font-weight="700">Shock</text>
  <line x1="394" y1="174" x2="426" y2="174" stroke="#22314d" stroke-width="3"/>
  <polygon points="426,156 456,174 426,192" fill="#ffe1cf" stroke="#22314d" stroke-width="3"/>
  <line x1="456" y1="156" x2="456" y2="192" stroke="#22314d" stroke-width="3"/>
  <text x="440" y="144" text-anchor="middle" font-size="12" fill="#6b7585">D_rebound</text>
  <line x1="456" y1="174" x2="498" y2="174" stroke="#22314d" stroke-width="3"/>
  <line x1="498" y1="150" x2="498" y2="198" stroke="#22314d" stroke-width="3"/>
  <line x1="512" y1="150" x2="512" y2="198" stroke="#22314d" stroke-width="3"/>
  <line x1="505" y1="198" x2="505" y2="220" stroke="#22314d" stroke-width="3"/>
  <line x1="486" y1="220" x2="524" y2="220" stroke="#22314d" stroke-width="3"/>
  <text x="505" y="238" text-anchor="middle" font-size="12" fill="#6b7585">C_relief</text>

  <rect x="620" y="92" width="250" height="160" rx="18" fill="#eefaf3" stroke="#cdeed9"/>
  <text x="640" y="124" fill="#22314d" font-size="18" font-weight="700">3) Codex current core</text>
  <circle cx="668" cy="154" r="18" fill="#fff" stroke="#4e79ff" stroke-width="3"/>
  <text x="668" y="159" text-anchor="middle" font-size="10" fill="#22314d" font-weight="700">EWY</text>
  <circle cx="668" cy="198" r="18" fill="#fff" stroke="#f28b44" stroke-width="3"/>
  <text x="668" y="203" text-anchor="middle" font-size="10" fill="#22314d" font-weight="700">SOX</text>
  <line x1="686" y1="154" x2="718" y2="154" stroke="#22314d" stroke-width="3"/>
  <line x1="686" y1="198" x2="718" y2="198" stroke="#22314d" stroke-width="3"/>
  <line x1="718" y1="154" x2="718" y2="198" stroke="#22314d" stroke-width="3"/>
  <line x1="718" y1="176" x2="752" y2="176" stroke="#22314d" stroke-width="3"/>
  <polygon points="752,158 784,176 752,194" fill="#fff2ad" stroke="#22314d" stroke-width="3"/>
  <line x1="784" y1="158" x2="784" y2="194" stroke="#22314d" stroke-width="3"/>
  <text x="768" y="146" text-anchor="middle" font-size="12" fill="#6b7585">D_semi</text>
  <line x1="784" y1="176" x2="826" y2="176" stroke="#22314d" stroke-width="3"/>
  <polyline points="826,176 838,162 850,190 862,162 874,190 886,162 898,176" fill="none" stroke="#22314d" stroke-width="3"/>
  <text x="862" y="150" text-anchor="middle" font-size="12" fill="#6b7585">R_flow</text>

  <line x1="278" y1="172" x2="324" y2="172" stroke="#6c7687" stroke-width="3" marker-end="url(#arr)"/>
  <line x1="574" y1="172" x2="620" y2="172" stroke="#6c7687" stroke-width="3" marker-end="url(#arr)"/>
  <text x="122" y="278" fill="#8a5b00" font-size="13" text-anchor="middle">단일 EWY 앵커</text>
  <text x="449" y="278" fill="#8a5b00" font-size="13" text-anchor="middle">급락·반등 보정층 삽입</text>
  <text x="744" y="278" fill="#8a5b00" font-size="13" text-anchor="middle">반도체·수급·레짐 복합 결합</text>

  <rect x="28" y="330" width="842" height="146" rx="18" fill="#fff" stroke="#eadfca"/>
  <text x="48" y="360" fill="#22314d" font-size="16" font-weight="700">최신 주차 핵심 변경점</text>
  {''.join(bullets)}
</svg>
"""


def build_html(rows: list[dict], week_dates: list[str], report_filename: str, latest_filename: str) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    codex_total = sum(r["codex_total_score"] for r in rows)
    claude_open_total = sum((r["claude_open_score"] or 0) for r in rows)
    codex_open_total = sum((r["codex_open_score"] or 0) for r in rows)
    codex_close_total = sum((r["codex_close_score"] or 0) for r in rows)
    best_day = max(rows, key=lambda r: r["codex_total_score"])
    worst_day = min(rows, key=lambda r: r["codex_total_score"])
    claude_adv_days = sum(1 for r in rows if "Claude" in r["winner"])
    labels = [d[5:] for d in week_dates]

    open_chart = line_chart_svg(
        labels,
        [
            {"name": "실제 시가", "color": "#2eae6b", "values": [r["actual_open"] for r in rows]},
            {"name": "Codex 시가", "color": "#4e79ff", "values": [r["codex_open"] for r in rows]},
            {"name": "Claude-style 시가", "color": "#f28b44", "values": [r["claude_open"] for r in rows]},
        ],
        "실측 시가 vs 예측 시가",
        "KOSPI open",
    )
    close_chart = line_chart_svg(
        labels,
        [
            {"name": "실제 종가", "color": "#2eae6b", "values": [r["actual_close"] for r in rows]},
            {"name": "Codex 종가", "color": "#4e79ff", "values": [r["codex_close"] for r in rows]},
        ],
        "실측 종가 vs Codex 12:30 종가 예측",
        "KOSPI close",
    )
    score_chart = bar_chart_svg(labels, rows)
    cum_chart = line_chart_svg(
        labels,
        [
            {"name": "Codex 누적 총점", "color": "#4e79ff", "values": [sum(rows[j]["codex_total_score"] for j in range(i + 1)) for i in range(len(rows))]},
            {"name": "Claude 누적 시가점수", "color": "#f28b44", "values": [sum((rows[j]["claude_open_score"] or 0) for j in range(i + 1)) for i in range(len(rows))]},
        ],
        "누적 점수 그래프",
        "tier score",
    )

    table_rows = []
    for r in rows:
        winner_cls = "codex" if "Codex" in r["winner"] else "claude" if "Claude" in r["winner"] else "draw"
        tags = ", ".join(r["failure_tags"][:2]) if r["failure_tags"] else "—"
        nexts = ", ".join(r["next_candidates"][:2]) if r["next_candidates"] else "—"
        table_rows.append(
            f"""
            <tr>
              <td>{r["date"]}</td>
              <td>{fmt_num(r["actual_open"])}</td>
              <td>{fmt_num(r["actual_close"])}</td>
              <td>
                <div><b>시가</b> {fmt_num(r["claude_open"])} · {fmt_score(r["claude_open_score"])}/5</div>
                <div class="sub">종가 공식기록 부재</div>
              </td>
              <td>
                <div><b>시가</b> {fmt_num(r["codex_open"])} · {fmt_score(r["codex_open_score"])}/5</div>
                <div><b>종가</b> {fmt_num(r["codex_close"])} · {fmt_score(r["codex_close_score"])}/5</div>
                <div class="sub">합계 {r["codex_total_score"]}/10 · {svg_escape(r["status_note"])}</div>
              </td>
              <td class="winner {winner_cls}">{r["winner"]}</td>
              <td>
                <div>{svg_escape(r["change_note"])}</div>
                <div class="small">failure_tags: {svg_escape(tags)}</div>
                <div class="small">next: {svg_escape(nexts)}</div>
              </td>
            </tr>
            """
        )

    week_start = week_dates[0]
    week_end = week_dates[-1]
    report_url = f"{PAGES_BASE}/{report_filename}"
    latest_url = f"{PAGES_BASE}/{latest_filename}"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KOSPI Claude vs Codex Weekly Report — {week_end}</title>
  <style>
    :root {{
      --bg:#fffdf9; --hero:#fff4d8; --card:#ffffff; --line:#eadfca; --ink:#1d2940; --sub:#627084;
      --blue:#4e79ff; --orange:#f28b44; --green:#2eae6b; --red:#e75b52; --gold:#8a5b00;
      --shadow:0 14px 34px rgba(145,112,32,.09);
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; color:var(--ink); background:linear-gradient(180deg,var(--hero) 0, var(--bg) 240px); line-height:1.6; }}
    .wrap {{ max-width:1240px; margin:0 auto; padding:28px 18px 56px; }}
    .hero,.card {{ background:var(--card); border:1px solid var(--line); border-radius:24px; box-shadow:var(--shadow); }}
    .hero {{ padding:28px; background:rgba(255,255,255,.82); }}
    .card {{ padding:22px; }}
    .grid {{ display:grid; grid-template-columns:repeat(12,1fr); gap:16px; margin-top:16px; }}
    .span-12 {{ grid-column:span 12; }} .span-6 {{ grid-column:span 6; }} .span-4 {{ grid-column:span 4; }}
    h1,h2,h3 {{ margin:0 0 10px; }} h1 {{ font-size:34px; }} h2 {{ font-size:23px; }} h3 {{ font-size:17px; }}
    .sub {{ color:var(--sub); }} .small {{ color:var(--sub); font-size:13px; }}
    .kpi {{ font-size:36px; font-weight:800; }} .tag {{ display:inline-block; padding:7px 10px; border-radius:999px; background:#fff2c7; color:#8a5b00; font-size:12px; font-weight:700; margin-right:8px; margin-top:6px; }}
    .legend {{ display:flex; gap:16px; flex-wrap:wrap; margin-top:8px; font-size:13px; color:var(--sub); }}
    .dot {{ width:11px; height:11px; border-radius:50%; display:inline-block; margin-right:6px; vertical-align:middle; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th,td {{ padding:12px 10px; border-bottom:1px solid #eee5d5; text-align:left; vertical-align:top; }}
    th {{ background:#fff8ea; font-size:13px; }}
    .winner.codex {{ color:var(--blue); font-weight:800; }}
    .winner.claude {{ color:var(--orange); font-weight:800; }}
    .winner.draw {{ color:var(--sub); font-weight:800; }}
    .two {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .callout {{ padding:16px 18px; background:#fff9eb; border:1px solid #ebcf88; border-radius:14px; }}
    .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; word-break:break-word; }}
    a {{ color:#2457d6; }}
    ul {{ margin:8px 0; padding-left:18px; }}
    @media (max-width: 920px) {{
      .span-6,.span-4 {{ grid-column:span 12; }}
      .two {{ grid-template-columns:1fr; }}
      h1 {{ font-size:28px; }}
      table {{ font-size:12px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>KOSPI Claude vs Codex 주간 종합 보고서</h1>
      <p class="sub">기준 주차: {week_start} ~ {week_end} · 생성시각: {generated} KST · 밝은 배경 반응형 · GitHub Pages 배포용 HTML</p>
      <div>
        <span class="tag">시가·종가 주간 데이터</span>
        <span class="tag">날짜별 점수/승패</span>
        <span class="tag">중요 모델 변경점</span>
        <span class="tag">실측 대비 시계열 그래프</span>
        <span class="tag">누적 점수 그래프</span>
        <span class="tag">전기회로도 스타일 모델 변화</span>
      </div>
    </section>

    <div class="grid">
      <section class="card span-4"><div class="sub">Codex 공식 누적점수</div><div class="kpi" style="color:var(--blue)">{codex_total}</div><div class="small">시가 {codex_open_total} + 종가 {codex_close_total}</div></section>
      <section class="card span-4"><div class="sub">Claude 누적 시가점수</div><div class="kpi" style="color:var(--orange)">{claude_open_total}</div><div class="small">daily log 잔존 inferred open 기준</div></section>
      <section class="card span-4"><div class="sub">주간 승부 해석</div><div class="kpi" style="font-size:26px">{claude_adv_days}일 Claude 시가 우위<br>{len(rows)-claude_adv_days}일 Codex/동률 우세</div><div class="small">공식 종가 기록은 Codex만 완전 보존</div></section>

      <section class="card span-12">
        <div class="callout">
          <b>핵심 요약.</b> 이번 주 Codex는 <b>{best_day["date"]}</b>에 {best_day["codex_total_score"]}/10으로 최고점을 기록했고, <b>{worst_day["date"]}</b>에는 {worst_day["codex_total_score"]}/10으로 가장 약했다.
          Claude는 저장소에 남은 <b>시가 inferred open</b> 기준으로만 비교 가능하다. 따라서 본 보고서는 <b>“Codex 공식 총점 + Claude 시가 비교 가능분”</b>을 결합한 전문가형 주간 리포트다.
        </div>
      </section>

      <section class="card span-6">
        <h2>실측 시가 vs 예측 시가</h2>
        <div class="legend">
          <span><span class="dot" style="background:#2eae6b"></span>실제 시가</span>
          <span><span class="dot" style="background:#4e79ff"></span>Codex 시가</span>
          <span><span class="dot" style="background:#f28b44"></span>Claude-style 시가</span>
        </div>
        {open_chart}
      </section>

      <section class="card span-6">
        <h2>실측 종가 vs Codex 종가 예측</h2>
        <div class="legend">
          <span><span class="dot" style="background:#2eae6b"></span>실제 종가</span>
          <span><span class="dot" style="background:#4e79ff"></span>Codex 12:30 종가 예측</span>
        </div>
        {close_chart}
      </section>

      <section class="card span-6">
        <h2>날짜별 점수 막대그래프</h2>
        <p class="small">오렌지 = Claude 시가 추정 점수(0~5), 파랑 = Codex 공식 총점(0~10)</p>
        {score_chart}
      </section>

      <section class="card span-6">
        <h2>누적 점수 그래프</h2>
        <p class="small">Codex는 시가+종가 공식 누적점수, Claude는 inferred open 누적점수</p>
        {cum_chart}
      </section>

      <section class="card span-12">
        <h2>모델 변화 과정</h2>
        {circuit_svg(rows)}
      </section>

      <section class="card span-12">
        <h2>날짜별 점수·승패·중요 변경점</h2>
        <table>
          <thead>
            <tr>
              <th>날짜</th>
              <th>실제 시가</th>
              <th>실제 종가</th>
              <th>Claude</th>
              <th>Codex</th>
              <th>승패</th>
              <th>중요 모델 변경점</th>
            </tr>
          </thead>
          <tbody>
            {''.join(table_rows)}
          </tbody>
        </table>
      </section>

      <section class="card span-12">
        <h2>전문가 코멘트</h2>
        <div class="two">
          <div>
            <h3>1) 구조적 관찰</h3>
            <ul>
              <li>이번 주는 급락 뒤 relief gap, avalanche sell, short-cover rebound, 반도체 melt-up이 한 주 안에 연속 출현했다.</li>
              <li>Codex는 매일 postmortem을 통해 시가·종가 엔진의 반복 실패를 규칙 소자처럼 추가했다.</li>
              <li>즉 핵심 우위는 단일 식보다 <b>실패 패턴을 빠르게 회로에 삽입하는 운영 적응성</b>에 있었다.</li>
            </ul>
          </div>
          <div>
            <h3>2) 데이터 해석 주의</h3>
            <ul>
              <li>Claude 최신 주차 기록은 저장소에 <b>공식 종가 시계열로 보존되지 않았다.</b></li>
              <li>따라서 양자 완전 대결이라기보다 <b>Codex 공식 리포트 + Claude 비교가능 시가</b> 형태다.</li>
              <li>향후 금요일 자동 리포트의 완전성을 위해서는 Claude 시가/종가 고정값도 동일 경로에 저장하는 것이 바람직하다.</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="card span-12">
        <h2>배포 경로</h2>
        <ul>
          <li>날짜 고정본: <a href="{report_url}">{report_url}</a></li>
          <li>최신 alias: <a href="{latest_url}">{latest_url}</a></li>
          <li>원천 로그: <span class="mono">contest/learning/daily_logs/{week_start}.json</span> ~ <span class="mono">contest/learning/daily_logs/{week_end}.json</span></li>
        </ul>
      </section>
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    week_dates = latest_week_dates()
    rows = build_rows(week_dates)
    week_end = week_dates[-1]
    report_filename = f"weekly_duel_report_{week_end}.html"
    latest_filename = "weekly_duel_report_latest.html"
    html = build_html(rows, week_dates, report_filename, latest_filename)
    report_path = DOCS_DIR / report_filename
    latest_path = DOCS_DIR / latest_filename
    report_path.write_text(html, encoding="utf-8")
    latest_path.write_text(html, encoding="utf-8")
    print(report_path)
    print(latest_path)


if __name__ == "__main__":
    main()
