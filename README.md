# KOSPI 시장 동역학 연구 — RC에서 다이오드 모델로

2026년 6월 KOSPI 급락·회복 동역학 연구. RC(맥스웰–바그너) 모델에서 출발해
**RLC + 다이오드 모델(v5)**로 발전, 604일 실데이터 백테스트로 검증.

> ⚔️ **경쟁 명시:** Codex가 RC v7로 활발히 경쟁 중. 다이오드 모델은 그에 대한 Claude의 구조적 응답이다.

## 📜 논문 연대기
**7월말 논문용 원자료 인덱스: [`PAPER_CHRONICLE.md`](PAPER_CHRONICLE.md)** — 모델 계보(v3→v7 회로도)·일일 전적·발견 목록·실패 박물관. 매일 갱신.

## 🔥 최신 산출물 (v5 다이오드 모델)

| 산출물 | 경로 | 내용 |
|--------|------|------|
| 🔌 **시뮬레이터** | `docs/index.html` | 인터랙티브 다이오드 모델 (GitHub Pages 배포) |
| 📄 **논문 PDF** | `claude/papers/v5_diode/*.pdf` | 국문·영문 정식 논문 |
| 📊 **백테스트** | `MODEL_v5_backtest.py` | 604일 실데이터 (H1 t=9.55) |
| 🔬 **모델 코드** | `MODEL_v4_RLC_diode.py`, `MODEL_v4b_honest_validation.py` | RC vs 다이오드 |
| 📡 **장중 모니터** | `monitor/kospi_diode_monitor.py` | D_sell 점화 경보 |
| 🏆 **점수표** | `SCORECARD.md` | 모델 변경 전/후 채점 |
| 📥 **데이터 수집** | `fetch_data.py`, `data/*.csv` | 재현용 |

**핵심 결과:** `D_sell = (외국인<0 AND 기관<0)` 다이오드가 시장 폭락을 점화.
604일 백테스트에서 D_sell ON 날 −1.19% vs OFF +0.68% (**t=9.55**), −5%↓ 폭락의 83% 포착.
**기관 부호(I)가 진짜 스위치** — RC의 외국인 게이트보다 우월.

> **시뮬레이터 배포:** GitHub → Settings → Pages → Source를 `main` 브랜치 `/docs`로 설정하면
> `https://waterfirst.github.io/kospi-mw-rc-research/` 에서 공개된다.

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
