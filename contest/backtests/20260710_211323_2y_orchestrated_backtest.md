# 2년 코스피 오케스트레이션 백테스트 — Codex Final Proxy 검증

## 1. 목적

- **최초 대결 시작 전 백테스트 결과**를 참고하고
- **현재 Codex 최종 모델의 백테스트 가능한 핵심 주장**을
- 과거 2년치 KOSPI 일봉+수급 데이터로 다시 검증했다.

## 2. 검증 범위

- 구간: 20240102 ~ 20260626
- 거래일 수: 604일
- ex-ante 테스트 행 수: 603일

## 3. 참고 기준(대결 시작 전)

### 3-1. Claude Diode v5 (기존 604일 기준)
- 당일 분류 강점이 핵심
- pre-duel 3M 참고:
  - 당일 ON 평균 -2.354%
  - 당일 OFF 평균 +2.020%
  - 익일 방향 정확도 57.9%

### 3-2. Codex MW-RC v7 proxy (대결 전 3개월)
- 기준 구간: 20260330~20260629
- 회복 신호일 수: 5
- 신호 방향 정확도: 60.0%
- 점예측 MAE: 2.906% vs naive 2.862%

## 4. 이번 2년 검증 결과

### 4-1. Diode v5 2Y
- D_sell ON 151일 / OFF 453일
- 당일 ON 평균 -1.191% vs OFF +0.677%
- 당일 방향 정확도 75.7%
- 당일 balanced accuracy 72.4%
- 급락(-2% 이하) 포착률 80.0% (n=40)
- 익일 방향 정확도 49.2%
- 익일 balanced accuracy 44.9%

### 4-2. Codex MW-RC pre-duel proxy 2Y
- 회복 신호 커버리지 4.6%
- 신호 방향 정확도 50.0%
- balanced accuracy 50.0%
- 신호일 평균 익일수익률 +0.461%
- 비신호일 평균 익일수익률 +0.198%

### 4-3. Codex vFinal daily-core proxy 2Y
- 신호 커버리지 17.2%
- 방향 정확도 48.9%
- balanced accuracy 46.9%
- UP 신호 평균 익일수익률 +0.235%
- DOWN 신호 평균 익일수익률 -0.070%
- 점예측 MAE 1.313% vs naive 1.278%

## 5. 전략 성과

### Diode ON 회피
- 총수익 +105.90%
- Sharpe 1.33
- MDD -19.37%

### Codex MW-RC pre-duel signal only
- 총수익 +11.86%
- Sharpe 0.45
- MDD -7.29%

### Codex vFinal daily-core long only
- 총수익 +18.64%
- Sharpe 0.55
- MDD -12.66%

### Codex vFinal daily-core long/short
- 총수익 +18.14%
- Sharpe 0.45
- MDD -16.21%

### Buy & Hold
- 총수익 +215.05%
- Sharpe 1.69
- MDD -20.67%

## 6. 해석

1. **Diode v5는 2년 구간에서도 “당일 위험 분류기”로서 유효한지**를 확인하는 기준선 역할을 한다.
2. **대결 전 MW-RC proxy**는 3개월 특수 국면보다 2년 전체에서 더 냉정하게 평가된다.
3. **vFinal daily-core proxy**는 현재 최종 Codex 모델의 전부가 아니라,  
   일봉 수급/전일 충격만으로 소급 가능한 핵심 사고를 검증한 것이다.
4. 따라서 이 결과는 **“최종 모델의 일봉 코어가 2년치에서 버티는가”**를 보는 검증이며,  
   실전 시가/종가 모델 전체 성능과 동일하다고 말하면 과장이다.

## 7. 한 줄 판정

- **Claude Diode**: 당일 위험 경보/급락 분류 기준선으로는 여전히 강함
- **Codex pre-duel proxy**: 3개월보다 2년에서 더 냉정하게 평가해야 함
- **Codex vFinal daily-core proxy**: 최종 모델의 일부 코어는 검증 가능하지만,  
  EWY/SOX/뉴스/장중 수급이 빠진 상태라 **완전한 최종 검증은 아님**

## 8. 한계

- 현재 최종 실전 모델의 EWY/SOX/뉴스/장중 수급/프로그램 입력은 2년 일봉 CSV에 없어 소급 불가
- 따라서 이 검증은 final model 전체가 아니라 daily-core proxy 검증
- 종가/시가 실전 점예측 성능과 1:1 동일시하면 안 됨
