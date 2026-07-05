# KakaoPay Securities KOSPI Regime MCP

카카오페이증권 사용자가 KOSPI 급변 원인을 이해하도록 돕는 설명 가능한 시장 레짐 분석 MCP입니다.

투자 추천이나 자동매매가 아니라, 미국장·EWY·반도체주·뉴스·수급을 전기회로 모델로 변환해 시가/종가 레짐과 근거를 설명합니다.

AX 해커톤 제출용 독립 repository입니다.

## 한 문장 요약

KOSPI 시장을 전기회로처럼 해석해 “왜 오늘 시장이 갭업/급락/반등/횡보 레짐인지”를 설명하는 카카오페이증권용 MCP입니다.

## 제출 정보

| 항목 | 내용 |
|---|---|
| 서비스 대상 | 카카오페이증권 앱 사용자, 리서치/콘텐츠 운영자 |
| 핵심 가치 | 단순 예측값이 아니라 시장 레짐과 근거를 설명 |
| 제출 ZIP | `dist/kakaopay_kospi_regime_mcp.zip` |
| 제출 답변 | `SUBMISSION_ANSWERS.md` |
| 주의 | 정보·연구·설명 보조 목적, 투자자문 아님 |

## 문제

개인 투자자는 밤사이 미국장, EWY, SOX, MU, NVDA, META, 환율, 뉴스, 외국인/기관/프로그램 수급을 한 번에 해석하기 어렵습니다. 증권사 운영자도 고객에게 “왜 오늘 시장이 이렇게 움직였는가”를 빠르게 설명해야 합니다.

## 핵심 아이디어

| 회로 소자 | 시장 의미 |
|---|---|
| `T_EWY` | 미국 시간의 한국 가격발견 변압기 |
| `V_semi` | SOX/MU/NVDA/META 반도체 전압 |
| `R_fx` | 환율·금리 저항 |
| `D_avalanche` | 외국인·프로그램 강제매도 다이오드 |
| `C_absorption` | 기관 매수 흡수 커패시터 |
| `S_news` | Meta/AWS/Azure 같은 서사 충격 스위치 |

## 제공 도구

| Tool | 설명 |
|---|---|
| `forecast_open` | KOSPI 시가 예측과 레짐 설명 |
| `forecast_close` | 장중 스냅샷 기반 종가 예측과 레짐 설명 |
| `explain_regime` | 입력 신호를 회로 소자로 해석 |
| `score_prediction` | 예측값과 실측값의 오차·점수 계산 |
| `submission_answers` | AX 해커톤 제출 문항 답변 반환 |

## 폴더 구조

```text
.
├─ README.md
├─ SUBMISSION_ANSWERS.md
├─ manifest.json
├─ requirements.txt
├─ DISCLAIMER.md
├─ kakaopay_kospi_regime_mcp/
│  ├─ server.py
│  ├─ core.py
│  └─ submission.py
├─ sample_outputs/
├─ tests/
├─ assets/
└─ dist/
   └─ kakaopay_kospi_regime_mcp.zip
```

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
python -m kakaopay_kospi_regime_mcp.server
```

MCP 클라이언트 설정 예:

```json
{
  "mcpServers": {
    "kakaopay-kospi-regime": {
      "command": "python",
      "args": ["-m", "kakaopay_kospi_regime_mcp.server"],
      "cwd": "PATH_TO_ZIP_EXTRACTED_FOLDER"
    }
  }
}
```

## 예시

### 시가 예측 입력

```json
{
  "prev_close": 8088.34,
  "prev_prev_close": 7648.09,
  "ewy_pct": -1.2,
  "sox_pct": -0.8,
  "mu_pct": -1.5,
  "nvda_pct": -0.6,
  "meta_pct": 0.2,
  "usdkrw": 1368,
  "negative_news_count": 1
}
```

### 출력

```json
{
  "forecast_open": 8039,
  "range": [7979, 8099],
  "regime": "stabilization_watch",
  "confidence": 0.56,
  "reason": ["EWY mild drag", "semi voltage weak", "no fresh shock"]
}
```

## 정보 부족 시 동작

- 입력이 부족하면 `confidence`를 낮추고 기본값을 사용합니다.
- 뉴스가 부족하면 수급·가격 신호를 우선합니다.
- 전일 급락 후 새 악재가 약하면 `post_crash_relief_possible`을 켭니다.
- 외국인·프로그램 매도가 임계값을 넘으면 `avalanche_sell`을 우선합니다.

## 검증 사례

`sample_outputs/`에 2026년 7월 초 사례를 넣었습니다.

- 7/2: Meta AI compute 뉴스와 반도체 매도 충격.
- 7/3: 전일 폭락 뒤 기관 매수 흡수 반등.

## 회로도

`assets/codex_final_global_gate_rc_vfinal.svg`에 최종 Gate-RC 회로도를 포함했습니다.

## 테스트

```bash
set PYTHONPATH=%CD%
python -m pytest tests -q
```

기대 결과:

```text
3 passed
```

## 주의

이 MCP는 정보·연구·설명 보조 목적입니다. 투자자문, 매수·매도 추천, 자동매매가 아닙니다.
