# Final Model Revision and Intraday Flow Nowcast

## 한 줄 결론

최종 모델은 이제

1. **시가 엔진**
2. **장중 수급 모니터**
3. **수급 nowcast(사전 추정)**
4. **종가 엔진**

의 4층 구조로 바꿔야 한다.

---

## 1. 지금까지 확인된 사실

### A. 시가 모델
- EWY 단독 앵커는 장기적으로 약하다
- 하지만 **SOX + 환율 + 전일 손상도 + 잔차보정**을 넣으면 개선 여지가 있다

### B. 종가 모델
- 진짜 edge는 **장중 외인/기관/프로그램 수급**
- 일봉만으로는 완전 재현이 안 된다
- 따라서 **장중 수급 모니터링 체계**가 모델의 핵심 인프라다

### C. 장기 레짐
- 장기 흐름은 별도 상위 모델(레짐/유동성 흐름 계층)로 다뤄야 한다

---

## 2. 최종 모델 수정 방향

## 2-1. 구조를 3엔진으로 분리

### Engine A. Open Engine
- 입력:
  - EWY
  - SOX
  - Nasdaq / S&P
  - USDKRW
  - 전일 국내 손상도(외인/기관/프로그램)
- 역할:
  - 시가 갭 예측
  - 과대 오버나잇 반응 압축

### Engine B. Flow Nowcast Engine
- 입력:
  - 개장 전/장초반 observable 변수
  - 전일 수급
  - 선물/환율/반도체 리더십
  - 일정 효과(만기일, MSCI 리밸런싱, 월말/월초)
- 역할:
  - 오늘 **외인/기관/프로그램이 어떤 방향으로 흐를 가능성이 높은지** 사전 추정

### Engine C. Close Engine
- 입력:
  - 09:00/10:30/12:00/12:30 장중 가격
  - 장중 외인/기관/프로그램 누적
  - breadth
  - 삼성전자 / SK하이닉스
  - 장중 저점 회복 여부
- 역할:
  - 종가 예측
  - avalanche / absorption / drift 판정

---

## 2-2. 플래그 수정 방향

### 유지
- `institution_absorption`
- `avalanche_sell`
- `gap_failed`
- `crash_continuation`

### 약화 또는 재정의
- EWY 단독 고정계수
- 모든 날에 같은 갭 반응 계수

### 추가
- `fx_pressure_high`
- `foreign_followthrough_risk`
- `opening_semiconductor_lead`
- `program_drag_risk`
- `expiry_day_distortion`
- `msci_rebalance_flow`

---

## 3. 장중 외인·기관 수급을 어떻게 모니터링할까

저장소에 이미 기반이 있다.

### 현재 사용 가능 소스
- `investorDealTrendDay`
- `programTrendInfo`
- 실시간 KOSPI snapshot
- 상승/하락 종목 수(breadth)
- 삼성전자 / SK하이닉스 가격 변화

### 권장 체크포인트
- **09:00**
- **09:10**
- **09:30**
- **10:30**
- **12:00**
- **12:30**
- **14:00**
- **15:00 직전**

### 왜 더 촘촘해야 하나
기존 09:00 / 10:30 / 12:00 / 12:30 만으론
- 개장 직후 외인 방향 전환
- 기관 방어 진입 시점
- 프로그램 급가속
을 놓칠 수 있다.

### 실전 모니터링 핵심 변수

#### 외국인
- 누적 순매수
- 10분 증가율
- 전환 시점(매도→매수 / 매수→매도)

#### 기관
- 누적 순매수
- 저점 부근에서 방어 유입 여부
- 외인 매도 대비 흡수 비율

#### 프로그램
- 총합
- 인덱스 / 비인덱스 분리 가능하면 분리
- 급격한 음수 확대 여부

#### 가격/구조
- 시가 대비 현재 위치
- 저가 회복률
- breadth
- 삼성전자 / 하이닉스 상대강도

---

## 4. 장중 수급을 미리 예측할 수 있는가

**완전 예측은 불가능**하지만,  
**사전 확률(nowcast)** 은 가능하다.

핵심은 “오늘 외인/기관이 사고 팔 가능성”을
개장 전 observable 변수로 미리 점수화하는 것이다.

---

## 4-1. 외인 수급 사전 추정 힌트

### 외인 매수 쪽 힌트
- EWY 강세
- 원화 강세(USDKRW 하락)
- SOX 강세
- 삼성전자/하이닉스 ADR/동종 반도체 강세
- 달러 약세
- 위험선호 회복

### 외인 매도 쪽 힌트
- 원화 약세
- 달러 강세
- 미 반도체 급락
- 지정학 뉴스
- 미국 장단기금리 급등
- 전일 한국장 급반등 후 차익실현 구간

---

## 4-2. 기관 수급 사전 추정 힌트

기관은 외인보다 “구조적/국내형” 성격이 강하다.

### 기관 매수 쪽 힌트
- 전일 급락 과도
- 밸류에이션 부담 완화
- 삼성전자/하이닉스 방어 필요 구간
- 연기금/펀드 리밸런싱 구간
- 외인 과매도 후 국내 방어 필요

### 기관 매도 쪽 힌트
- 이미 전일 큰 방어 소진
- 월말/분기말 window dressing 종료
- 종목 차익실현
- 반등 함정 구간

---

## 4-3. 프로그램 수급 사전 추정 힌트

프로그램은 가장 예측이 어렵지만,
일부는 구조적으로 접근 가능하다.

### 힌트
- 선물-현물 베이시스
- KOSPI200 선물 방향
- 미국 지수선물
- 삼성전자/하이닉스 대형주 동조
- 만기일 / 동시호가 왜곡
- ETF 리밸런싱

즉 프로그램은 **가격 결과를 따라가는 힘**도 크기 때문에  
“원인”이라기보다 **증폭기**로 다루는 편이 좋다.

---

## 5. 추천하는 nowcast 구조

## 5-1. 외인 nowcast score

```text
foreign_score =
  + a1 * EWY
  + a2 * SOX
  - a3 * USDKRW_change
  - a4 * DXY
  + a5 * Samsung_relative_strength
  + a6 * Hynix_relative_strength
  + a7 * overnight_risk_on
```

결과:
- score > threshold → 외인 순매수 가능성
- score < threshold → 외인 순매도 가능성

---

## 5-2. 기관 nowcast score

```text
inst_score =
  + b1 * prior_day_drawdown
  - b2 * prior_day_inst_exhaustion
  + b3 * valuation_relief
  + b4 * semiconductor_defense_need
  + b5 * domestic_stabilization_signal
```

결과:
- 급락 후 방어 가능성 추정
- 외인 매도 흡수 여부 추정

---

## 5-3. 프로그램 risk score

```text
program_risk =
  + c1 * futures_basis_stress
  + c2 * index_heavy_selloff
  + c3 * expiry_effect
  + c4 * ETF_rebalance_signal
```

결과:
- 장중 하방 가속 가능성 경고

---

## 6. 최종 종가 예측 엔진 수정안

기존 deterministic close forecast는 좋은 뼈대를 갖고 있다.
여기에 아래를 추가하는 것이 좋다.

### 추가 1. 수급 가속도
- 단순 누적치보다
- **최근 10~20분 증가속도** 반영

예:
- 외인 -5천 → -1.5만으로 급가속
- 기관 +1만 → +3만으로 급가속

### 추가 2. 흡수비율

```text
absorption_ratio = institution_buy / max(abs(foreign_sell), 1)
```

- 0.8 이상이면 방어 가능성
- 0.4 이하면 외인 압도

### 추가 3. 저가회복률

```text
low_recovery_ratio = (current - low) / max(high - low, 1)
```

- 낮은데 외인 매도 심하면 continuation
- 높은데 기관 방어 강하면 rebound

### 추가 4. breadth regime
- 상승종목 수/하락종목 수가 좁으면
  대형주 착시 상승 가능성 경고

### 추가 5. 프로그램 증폭기
- 프로그램 음수 확대 시
  외인 매도와 결합하면 avalanche 가중

---

## 7. 오늘 기준 실전 운영안

### 개장 전
- Open Engine 실행
- 외인/기관/프로그램 nowcast score 계산

### 09:10
- 첫 수급 확인
- nowcast와 실제 부호 비교
- mismatch 발생 시 신뢰도 하향

### 10:30
- 외인 추세 지속/전환 확인
- 기관 흡수 여부 확인

### 12:30
- 종가 엔진 본 예측
- avalanche / absorption / drift 최종 판정

### 14:00 이후
- program 가속 여부로 종가 미세조정

---

## 8. 한 줄 판정

### 질문 1. 장중 수급 모니터링은 가능한가?
- **예, 이미 가능하다**
- 다만 체크포인트를 더 촘촘하게 해야 한다

### 질문 2. 장중 수급을 미리 예측할 수 있는가?
- **완전 예측은 불가**
- 그러나 **외인/기관/프로그램의 확률적 nowcast는 충분히 가능**

### 질문 3. 최종 모델 수정 방향은?
- **시가 엔진 + 수급 nowcast + 장중 종가 엔진**으로 분리

