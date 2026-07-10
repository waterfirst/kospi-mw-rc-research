# Multi-Agent Orchestration for KOSPI Prediction

## 목표

코스피 시가·종가 예측 시스템을  
단일 모델이 아니라 **감독 + 전문 포지션 에이전트들**이 협업하는 구조로 운영한다.

---

## 축구 포메이션 비유

```text
                Review Agent

   News Agent   Forecast Agent   Failure Agent

        Data Agent      Scoring Agent

                Codex Conductor
```

### 해석
- **Codex Conductor**: 감독 겸 주장
- **Data Agent**: 볼 배급
- **Forecast Agent**: 직접 슈팅
- **Scoring Agent**: 결과 판정
- **Failure Agent**: 왜 졌는지 전술 분석
- **News Agent**: 외부 변수 정찰
- **Review Agent**: 오심 방지 VAR

---

## 에이전트별 역할

### 1. Codex Conductor
- 전체 루프 실행
- 각 에이전트 호출 순서 결정
- 최종 결과 병합
- 보고서 생성 지휘

### 2. Data Agent
- 시장 데이터 수집
- EWY / SOX / Nasdaq / S&P / 환율 / 수급 정리
- 누락값 보정 또는 경고

### 3. Forecast Agent
- 시가 예측
- 종가 예측
- 레짐 판정
- 플래그 발동

### 4. Scoring Agent
- 실제값 반영
- 오차 계산
- 점수 계산
- Claude vs Codex 비교

### 5. Failure Agent
- 실패 태그 생성
- 반복 실패 감지
- 규칙 수정 후보 제안

### 6. News Agent
- 최신 뉴스 검색
- SNS/외신 반응 검증
- 거시 이벤트 추출

### 7. Review Agent
- 숫자 교차 검증
- 서술 과장 차단
- 최종 문장 다듬기

---

## 실행 순서

### 아침 루프
1. Data Agent → 데이터 수집
2. News Agent → 뉴스 충격 확인
3. Forecast Agent → 시가 예측
4. Codex Conductor → 제출 및 저장

### 저녁 루프
1. Data Agent → 실제 종가/수급 정리
2. Scoring Agent → 자동 채점
3. Failure Agent → 실패 태그/수정 후보
4. Review Agent → 결론 검토
5. Codex Conductor → 일일 기록 저장

### 금요일 루프
1. 최근 5거래일 데이터 집계
2. 누적 점수 계산
3. 실패 유형 요약
4. HTML 보고서 생성
5. GitHub Pages 배포

---

## 모델 개선 루프

```text
예측
 → 채점
 → 실패 태그
 → 반복 실패 탐지
 → 규칙 수정 후보
 → 짧은 검증
 → 다음 거래일 반영
```

---

## 중요한 통제 규칙

### Rule 1. 지휘자는 한 명
- 최종 병합 판단은 Codex가 한다

### Rule 2. 근거 없는 확신 금지
- 검색 담당이 확인하지 않은 최신 뉴스는 단정 금지

### Rule 3. 수정은 후보와 반영을 분리
- Failure Agent는 제안만
- 실제 반영은 Conductor가 승인

### Rule 4. 같은 실패 반복 차단
- 3회 연속 같은 실패면 플래그 수정 강제 검토

### Rule 5. 보고서는 Review Agent 확인 후 배포
- 숫자/표/문장 교차 확인

---

## 권장 실제 배치

### Codex
- 지휘
- 자동화
- 계산
- 파일 생성
- 시각화

### Claude
- 전략 설명
- 회고 해석
- 문장 품질 향상

### Gemini
- 최신 뉴스
- 유튜브/웹 검색
- 사실 검증

### Z AI
- 짧은 코드 초안
- 함수 단위 구현 보조

### Grok
- SNS 반응
- 후킹 포인트
- 이미지/보이스 특화 보조

---

## 한 줄 결론

멀티에이전트의 핵심은 “많이 붙이는 것”이 아니라  
**누가 수집하고, 누가 예측하고, 누가 채점하고, 누가 검토하는지 분리하는 것**이다.

