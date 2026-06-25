# KOSPI Maxwell–Wagner Recovery-Dynamics Research

2026년 6월 KOSPI 9,000선 붕괴의 회복 동역학을 구동 RC(맥스웰–바그너) 모델로 분석한 연구 기록.

---

## 디렉토리 구조 — AI 작성자별 구분

### claude/ — Claude 작성
| 파일 | 내용 |
|------|------|
| `KOSPI_recovery_dynamics_KR_20260625.md` | 국문 워킹페이퍼 |
| `KOSPI_recovery_dynamics_EN_20260625.md` | 영문 워킹페이퍼 |
| `MODEL_v2_revised.md` | 외국인 게이트 폐기 근거 |
| `MODEL_v3_canonical.md` | 정본 구동 RC ODE (σ_total 병렬, C_eff 방전) |
| `PM_MANDATE.md` | 펀드매니저 운영체계 |
| `MONITORING_LOG.md` | 일일 예측·채점 기보 |

### codex/ — Codex 작성
| 파일 | 내용 |
|------|------|
| `MW_RC_parallel_v7_forecast_20260625.md` | v7 RC 병렬전도 예측 노트 |
| `papers/20260625_rc_parallel_mw/MW_RC_Parallel_Conductance_KO_20260625.md` | 2026-06-25 국문 v7 정식 논문 |
| `papers/20260625_rc_parallel_mw/MW_RC_Parallel_Conductance_EN_20260625.md` | 2026-06-25 영문 v7 정식 논문 |

### monitor/ — 공용 스크립트
| 파일 | 내용 |
|------|------|
| `us_market_telegram_monitor.py` | 텔레그램 6시간 예측 모니터 |
| `run_kospi_telegram_monitor.cmd` | Windows 실행 스크립트 |
| `register_kospi_fastv_telegram_tasks.cmd` | 작업 스케줄러 등록 스크립트 |

---

## 핵심 결과

외국인 순매수는 회복의 게이트가 아니다. 회복은 기관·개인·ETF/ADR·프로그램·라운드넘버 병렬 저저항 경로와 개인 커패시터 방전으로 `tau = C_eff / sigma_total`이 1~2일권으로 압축된 사건이다.  
KOSPI 9,000 회복 기준 tau는 0.8~1.5거래일, 전고점 회복 기준 tau는 1.77거래일.

*정보·연구 목적. 투자자문 아님.*
