# CLAUDE.md — 첨물(nakcho.choi@gmail.com) 전역 그라운드 룰
> 모든 프로젝트에 자동 적용. 이 파일을 항상 먼저 읽어라.
> 최종 수정: 2026-06-29
> 규칙: 프로젝트 완료 시 섹션 10(시행착오 누적)에 반드시 추가

---

## ★ 세션 부팅 — 기억 먼저 로드 (최우선)
> 모든 대화 시작 시 아래 순서로 `D:\nakcho\python\claude-memory\` 를 먼저 읽는다.
> repo: https://github.com/waterfirst/claude-memory (private). 없으면 `git clone` 후 진행.

1. `claude-memory\CONSTITUTION.md` — 최상위 헌법 (모든 규칙 우선)
2. `claude-memory\MEMORY.md` — 기억 인덱스 (필요 항목만 lazy load)
3. `claude-memory\core\now.md` — 현재 상태/진행 작업
4. `claude-memory\semantic\diary.md` 최근 3일 — 맥락 이어가기

- 경로 주의: 헌법 내 `/home/ubuntu/.cokacdir/...` 는 Linux 서버용. 이 PC에선 `D:\nakcho\python\claude-memory\` 로 대응.
- 기억 변경 시 commit + push (헌법 제1조 6항).

---

## 0. 기본 원칙

- 한국어로 응답
- 핵심 먼저, 불필요한 설명 없음
- 작업 전 계획 → 승인 → 실행 순서 준수
- 모든 작업은 `D:\nakcho\python\` 아래에서

---

## 1. 프로젝트 구조 규칙

### 폴더 명명
```
D:\nakcho\python\
├── CLAUDE.md                  ← 이 파일 (전역 규칙)
├── skills\                    ← 재사용 스킬 라이브러리
│   ├── superpowers\           ← obra/superpowers (다운로드 필요)
│   ├── context-engineering\   ← muratcankoylan (다운로드 필요)
│   ├── awesome-claude\        ← ComposioHQ (다운로드 필요)
│   └── custom\                ← 첨물 전용 커스텀 스킬
├── cowork_{프로젝트명}_{YYYYMMDD}\   ← 신규 프로젝트
│   ├── report.html            ← 자기완결 HTML 결과물
│   ├── Agent.md               ← 에이전트 역할 분담 기록
│   ├── SKILL.md               ← 기술 패턴 정리
│   └── METRICS.md             ← 성과지표
```

### 프로젝트 시작 전 체크리스트
- [ ] GLM 연결 테스트 (`skills/custom/glm-connection.md` 참조)
- [ ] 기존 스킬 라이브러리에서 재사용 가능한 것 확인
- [ ] 계획 → 사용자 승인 → 실행

---

## 2. 에이전트 역할 분담 (토큰 최소화)

| 담당 | 역할 | 비고 |
|------|------|------|
| **Claude** | 설계, 코드 작성, HTML 구조 | 정확도 필요 항목만 |
| **GLM4:9b** | 텍스트 해석, 요약, 설명 | Ollama 연결 필요 |
| **numpy** | 수치 계산 (C-backend) | 500K paths/55ms |
| **scipy** | 최적화 솔버 | SLSQP, minimize |
| **내장 폴백** | GLM 미연결 시 대체 텍스트 | 사전 정의 문자열 |

### GLM 연결 주소 (sandbox → Windows)
```python
# 틀린 방법
OLLAMA_URL = "http://localhost:11434"  # sandbox 자신

# 올바른 방법 (우선순위 순)
candidates = ["host.docker.internal", "172.17.0.1", "192.168.65.1"]
```

### Claude 토큰 목표
| 조건 | 목표 |
|------|------|
| GLM 미연결 | ≤ 8,000 |
| GLM 연결 | ≤ 2,500 |

---

## 3. 속도 최적화 규칙

### If-Then 규칙
- 경로 수 < 100K → numpy 기본
- 경로 수 ≥ 100K → numpy 벡터화 (루프 금지)
- 경로 수 ≥ 1M → C 컴파일 (`-O3 -march=native -ffast-math`)
- 시각화 → matplotlib base64 (R ggplot2 필요 시 PowerShell 연동)

### 속도 기준
| 방법 | 기준 |
|------|------|
| numpy 벡터화 | 500K paths ≤ 100ms |
| scipy SLSQP | 100포인트 ≤ 5초 |
| matplotlib | 차트 5개 ≤ 2초 |
| 전체 파이프라인 | ≤ 15초 |

---

## 4. 산출물 기준

### 필수 파일 (프로젝트 완료 시)
```
report.html   자기완결 HTML (base64 차트 임베딩)
Agent.md      에이전트 역할 분담 + 파이프라인 기록
SKILL.md      재사용 기술 패턴 + 다음 확장 방향
METRICS.md    토큰 수 / 실행시간 / 리포트 수준 / 사용언어 / Agent 구성
```

### HTML 리포트 품질 기준
- 다크테마 (Catppuccin Mocha: #1e1e2e)
- KPI 카드 + 차트 + 해석 텍스트 + 테이블 필수 포함
- 파일 크기 200~500KB
- 한국어 폰트 명시 (Malgun Gothic / Noto Sans CJK)

---

## 5. 스킬 라이브러리 사용 규칙

### 프로젝트 시작 시 스킬 확인 순서
1. `skills/superpowers/` — 계획/실행/디버깅
2. `skills/context-engineering/` — 컨텍스트 최적화
3. `skills/awesome-claude/` — 특수 기능
4. `skills/custom/` — 첨물 전용 스킬

### 스킬 다운로드
```powershell
cd D:\nakcho\python\skills
.\download_skills.ps1
```

---

## 6. 디스플레이 기술 컨텍스트 (Samsung Display)

첨물은 Samsung Display Principal Engineer (OLED/LCD/Micro LED).
기술 질문 시:
- 마이크로캐비티, EQE, OLED 수명, 구동회로 → 전문가 수준 응답
- 특허 분석 → IPC 분류 포함
- 논문/특허 요약 → 핵심 novelty 먼저

---

## 7. 투자 컨텍스트

- 퇴직연금 (IRP/DC) 포함 포트폴리오
- 한국/미국 ETF 혼합
- 리스크 지표: Sharpe, VaR95%, MDD
- 최적화: Markowitz SLSQP 또는 Black-Litterman

---

## 8. 금지 사항

- [ ] `localhost`로 Ollama 연결 시도 (host.docker.internal 사용)
- [ ] 루프로 Monte Carlo 계산 (numpy 벡터화 필수)
- [ ] 프로젝트 완료 시 METRICS.md 누락
- [ ] 한국어 응답 누락
- [ ] 불필요한 설명/서문 (`Let me...`, `Sure, I will...` 금지)

---

## 9. GLM 폴백 정책

```python
GLM_TIMEOUT = 30.0  # 30초 초과 시 폴백

# 폴백 우선순위
1. GLM4:9b (Ollama, RTX 5060)
2. Claude Haiku API (ANTHROPIC_API_KEY 설정 시)
3. 내장 폴백 텍스트 (사전 정의)
```

---

---

## 10. 시행착오 누적 로그
> 프로젝트 완료 시 여기에 추가. 같은 실수 반복 금지.

---

### [P001] cowork_글로벌ETF포트폴리오분석_20260628

**성과:** Monte Carlo 10K paths, 차트 5개, HTML 349KB, 실행 ~8초  
**토큰:** Claude ~8,500 / GLM 0

| # | 시행착오 | 원인 | 다음부터 |
|---|---------|------|---------|
| 1 | GLM 미연결로 텍스트 섹션 Claude가 직접 처리 | `localhost` 사용 | `host.docker.internal` 사용 |
| 2 | 토큰 8,500으로 목표 초과 | HTML+텍스트 전부 Claude | 텍스트는 GLM 위임 |

---

### [P002] cowork_옵션리스크엔진_20260628

**성과:** BS+Heston MC 200K paths + Markowitz 80pt, 차트 4개, HTML 285KB, 총 7,418ms  
**토큰:** Claude ~7,900 / GLM 0

| # | 시행착오 | 원인 | 다음부터 |
|---|---------|------|---------|
| 1 | GLM 또 미연결 | sandbox `localhost` 재사용 | 프로젝트 시작 시 GLM 연결 테스트 먼저 (체크리스트 항목 1) |
| 2 | C 바이너리 sandbox 타임아웃 | 1M 반복을 sandbox에서 실행 | C는 Windows에서 컴파일, sandbox에선 numpy 벡터화 |
| 3 | Julia/Rust 미설치 | sandbox에 없음 | 속도 필요 시 C(GCC) 또는 Numba JIT 사용 |
| 4 | Heston 가격(1,587) BS(3,192) 대비 너무 낮음 | ρ=-0.7 강한 음의 상관 + 단기 paths | steps 수 늘리거나 ρ 재검토 |
| 5 | httpx 미설치로 1회 오류 | 환경 확인 생략 | 시작 전 `pip list` 체크 또는 requirements 먼저 설치 |

---

### 공통 패턴 (모든 프로젝트)

| 패턴 | 해결책 |
|------|--------|
| GLM 미연결 반복 | **프로젝트 첫 줄에 GLM 연결 테스트 코드 삽입 필수** |
| Claude 토큰 초과 | 텍스트 섹션(3~4개) → GLM 위임으로 40% 절감 |
| sandbox 패키지 누락 | 코드 시작 전 `pip install [필요패키지] --break-system-packages` |
| 한국어 폰트 경고 | `NotoSansCJK-Regular.ttc` 경로 명시 (sandbox에 존재) |
| 차트 superscript 글자 깨짐 | 특수문자(⁶ 등) 대신 `x10^6` 텍스트 사용 |

---

*이 파일은 `D:\nakcho\python\CLAUDE.md`에 위치. 모든 cowork 프로젝트에서 참조.*
