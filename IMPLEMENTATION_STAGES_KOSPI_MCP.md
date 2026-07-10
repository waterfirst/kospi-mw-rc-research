# KOSPI MCP 단계별 구현 계획

## 목표

벽돌깨기식 코스피 시가·종가 예측 시스템을  
**기록 → 채점 → 실패분석 → 규칙개선 → 보고서 → MCP화** 순서로 구현한다.

---

## 1단계. 일일 로그 자동 저장기

### 목적
- 매일 예측과 실제값을 구조적으로 쌓는다
- 학습의 재료를 만든다

### 구현 항목
- 예측 결과 JSON 저장
- 입력 변수 저장
- 사용 플래그 저장
- 모델 버전 저장

### 산출물
- `contest/learning/daily_logs/YYYY-MM-DD.json`
- `contest/learning/daily_logs/_template.json`

### 구현 파일
- `monitor/save_daily_log.py`

### 완료 기준
- 하루 1회 실행 시 JSON 파일이 자동 생성됨
- 수동 복붙 없이 기록 가능

---

## 2단계. 자동 채점기

### 목적
- 시가/종가 예측을 점수로 바꾼다
- Claude vs Codex 비교 가능하게 만든다

### 구현 항목
- 시가 오차 점수 계산
- 종가 오차 점수 계산
- 방향성 점수 계산
- 총점 계산

### 산출물
- 일일 로그 내 `scores`
- 별도 점수 요약 JSON/CSV

### 구현 파일
- `monitor/score_daily_prediction.py`

### 완료 기준
- 실제값 입력 후 자동 채점 완료
- 날짜별 점수표 생성 가능

---

## 3단계. 실패 태그 자동 분류기

### 목적
- “틀렸다”를 끝내지 않고 왜 틀렸는지 구조화한다

### 구현 항목
- 반도체 리더십 누락 탐지
- 환율 영향 과소/과대 탐지
- 뉴스 충격 누락 탐지
- 수급 해석 오류 탐지
- 갭 피로도 누락 탐지

### 산출물
- `failure_tags`
- `reflection.summary`

### 구현 파일
- `monitor/tag_failure_patterns.py`

### 완료 기준
- 채점 후 자동으로 실패 태그 부여
- 최근 20일 실패 유형 집계 가능

---

## 4단계. 규칙 후보 제안기

### 목적
- 같은 실패가 쌓이면 모델 수정 후보를 자동 제안한다

### 구현 항목
- 최근 실패 유형 빈도 계산
- 반복 실패 경고
- 새 플래그 후보 생성
- 기존 플래그 약화/비활성 후보 생성

### 산출물
- `contest/learning/candidates/rule_update_queue.json`

### 구현 파일
- `monitor/propose_rule_updates.py`

### 완료 기준
- 최근 20거래일 기준 규칙 수정 후보 자동 생성
- 사람이 후보만 검토하면 됨

---

## 5단계. 주간 HTML 종합 보고서

### 목적
- 한 주간의 성과와 실패를 사람이 빠르게 이해하게 만든다

### 구현 항목
- 날짜별 점수표
- 누적 점수 그래프
- 실측 vs 예측 시계열
- 모델 변화 과정 회로도
- 실패 유형 요약

### 산출물
- `docs/weekly_report_YYYY_WW.html`
- 고정 링크 별칭

### 구현 파일
- `monitor/render_weekly_report.py`

### 완료 기준
- 매주 금요일 자동 생성
- GitHub Pages에 자동 배포

---

## 6단계. MCP 인터페이스화

### 목적
- AI가 직접 조회·예측·채점·회고할 수 있게 만든다

### 구현 항목
- `get_market_snapshot`
- `predict_open`
- `predict_close`
- `score_prediction`
- `analyze_failure_patterns`
- `render_weekly_report`

### 산출물
- MCP 서버
- manifest / README / examples

### 구현 파일
- `mcp_kospi_diode/server.py`
- `mcp_kospi_diode/core.py`

### 완료 기준
- Claude/Codex가 MCP 도구로 직접 사용 가능
- 예측/채점/회고/보고서가 도구 호출로 이어짐

---

## 7단계. 오케스트레이션 멀티에이전트화

### 목적
- 한 에이전트가 모든 일을 다 하지 않고
- **수집 / 계산 / 해석 / 검토 / 보고**를 역할별로 분리한다

### 기본 원칙
- **지휘자는 1명**이어야 한다
- 각 에이전트는 **짧고 명확한 책임**만 가진다
- 결과는 반드시 **공용 로그 포맷**으로 다시 합쳐진다

### 권장 포지션

#### 1. Conductor (지휘자)
- 전체 작업 순서 제어
- 어떤 에이전트에게 무엇을 시킬지 결정
- 최종 판단 및 산출물 확정

#### 2. Data Agent
- 미국장 / 반도체 / 환율 / 수급 / 뉴스 수집
- 입력 데이터 정리
- 누락 데이터 탐지

#### 3. Forecast Agent
- 시가 예측
- 종가 예측
- 레짐 판정
- 신뢰도 추정

#### 4. Scoring Agent
- 실제값 반영
- 점수 계산
- Claude vs Codex 비교

#### 5. Failure Analysis Agent
- 왜 틀렸는지 태그 분류
- 반복 실패 구조 탐지
- 규칙 수정 후보 제안

#### 6. Report Agent
- 일간 요약
- 주간 HTML 보고서
- 그래프 / 회로도 / 표 정리

#### 7. Review Agent
- 숫자/문장 교차검토
- 과장된 해석 차단
- 잘못된 결론 경고

### 구현 항목
- 에이전트별 입력/출력 규격 정의
- 지휘자 프롬프트 정의
- 결과 병합 규칙 정의
- 실패 시 fallback 순서 정의

### 산출물
- `MULTI_AGENT_ORCHESTRATION_KOSPI.md`
- 지휘 프롬프트
- 에이전트 역할 프롬프트

### 구현 파일
- `monitor/orchestrate_kospi_agents.py`
- `monitor/agent_roles/`

### 완료 기준
- 한 번의 지시로
  - 데이터 수집
  - 예측
  - 채점
  - 실패분석
  - 보고서 생성
  가 순차 또는 병렬로 실행됨

---

## 추천 구현 순서

### 먼저 할 것
1. `save_daily_log.py`
2. `score_daily_prediction.py`
3. `tag_failure_patterns.py`

### 그 다음
4. `propose_rule_updates.py`
5. `render_weekly_report.py`

### 마지막
6. MCP 인터페이스로 통합
7. 오케스트레이션 멀티에이전트화

---

## 운영 루프

```text
아침:
  데이터 수집 → 시가 예측 저장

장중/종가:
  종가 예측 저장 → 실제값 반영

저녁:
  자동 채점 → 실패 태그 → 회고 로그 저장

금요일:
  주간 보고서 생성 → GitHub Pages 배포

상위 제어:
  지휘자 에이전트가 전체 순서 및 검토를 오케스트레이션
```

---

## 이번 주 바로 착수할 3개

### A. 일일 로그 자동 저장기
- 가장 먼저 필요

### B. 자동 채점기
- 점수 없이는 학습도 없음

### C. 실패 태그 분류기
- 벽돌깨기식 개선의 핵심

---

## 멀티에이전트 권장 역할 분담

- **Codex**: 구조화, 계산, 로그 저장, 시각화, 자동화
- **Claude**: 해석, 회고, 전략 정리, 리스크 설명
- **Gemini**: 최신 뉴스/검색 검증
- **Z AI**: 짧은 코드 초안/보조 구현
- **Grok**: 대중 반응, SNS 화제성, 이미지·보이스 보조

즉,

```text
Codex = 감독 + 엔지니어
Claude = 수석 해설 + 전략 코치
Gemini = 외신 / 검색 담당
Z AI = 코더 보조
Grok = SNS / 이미지 특화 보조
```

---

## 한 줄 결론

**1단계는 기록, 2단계는 채점, 3단계는 실패분석**이다.  
이 세 개가 완성되면 그 다음부터는 모델이 “경험을 쌓는 구조”가 된다.  
그리고 최종적으로는 **오케스트레이션 멀티에이전트**가 그 경험을 더 빠르게 증폭시킨다.
