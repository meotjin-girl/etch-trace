# TRACE | 식각 공정 이상 조사 AI Agent

**SKALA AI Agent Capstone**

반도체 식각 공정 이상을 과거 데이터와 SOP 근거로 즉시 비교·추적하고, 엔지니어 승인 이력을 자산화하는 식각 이상 조사 AI Agent

- **제안 팀**: 판교 3반 | P070 김준영, P077 봉혜린, P081 오다연, P083 이규빈, P097 조용진, P099 주윤겸
- **제안 대상**: 반도체 제조사 식각 공정·설비 기술 조직, 제조 IT 조직
- **주제**: AI Agent Capstone

---

## 목차

1. [개요](#s1)
2. [비즈니스 가치](#s2)
3. [Excursion의 사업적 영향](#s3)
4. [솔루션 제안](#s4)
5. [아키텍처](#s5)
6. [AI Agent 설계](#s6)
7. [MCP Server 설계](#s7)
8. [AI Agent 구현 설계](#s8)
9. [Harness 설계](#s9)
10. [화면·업무 API·인증](#s10)
11. [기대 효과 및 KPI](#s11)
12. [시장 사례로 본 효과](#s12)
13. [대안 비교 및 선정 근거](#s13)
14. [산업 동향](#s14)
15. [도입 로드맵과 확장 계획](#s15)
16. [최종 시연 계획](#s16)
17. [리스크 및 대응](#s17)
18. [결론 및 요청 사항](#s18)
19. [출처](#s19)

---

<a id="s1"></a>

## 1. 개요

### 1.1 제안 요약

| 구분 | 내용 |
|---|---|
| 과제 | 식각 공정 이상이 감지된 뒤의 **조사 단계**가 엔지니어 수작업에 의존하여, 웨이퍼 보류(Lot Hold) 해제와 장비 처리 판단까지 시간이 오래 걸리고 담당자마다 조사 품질이 다름 |
| 제안 | 과거 사례·계측 수치·SOP 조항을 연결해 조사 보고서 초안을 만들고, 엔지니어 검토·승인으로 공식 이력을 남기는 AI Agent **TRACE** 도입 |
| 대상 공정 | **식각**. 가장 자주 반복되고, 투자 비중이 크며, 수율에 민감하고, 센서 데이터가 풍부한 공정 (2장). 건식 식각(이온밀) 데이터로 먼저 검증하고 건식·습식 전체로 확장 (15장) |
| 적용 범위 | 이상 대응 5단계 중 ②조사, ⑤기록. 판정과 조치는 엔지니어 권한으로 유지 |
| 차별점 | 5단계 전문 조사 · 숫자는 코드가 계산 · 반환된 문서 조항에 출처 연결 · 엔지니어 승인 스냅샷만 공식 이력 저장 |
| 도입 방식 | PoC → 단일 장비군 Pilot → 라인 확장, 사내망 설치형 |

---

<a id="s2"></a>

## 2. 비즈니스 가치

### 2.1 반도체 설비 투자 동향

AI 수요로 메모리 중심의 설비 투자가 크게 늘고 있습니다. 장비가 늘면 관리할 챔버와 이상 건수도 함께 늘어납니다.

#### 세계 반도체 장비 매출

*단위 USD 억 · 점선은 전망치, 2027년은 미공개*

![세계 반도체 장비 매출](<contents/figures/s2-01.png>)

<sub>SEMI 2026.4, 2026.7</sub>

#### 2025년 지역별 장비 매출

*단위 USD 억 · 한국 3위, 전년 대비 +26%*

![2025년 지역별 장비 매출](<contents/figures/s2-02.png>)

<sub>SEMI 2026.4</sub>

### 2.2 식각 공정 난이도 상승

- **식각** (Etch): 노광으로 찍은 회로 모양대로, 필요 없는 막을 플라즈마나 약액으로 깎아 제거하는 공정입니다.
- **종횡비** (Aspect Ratio): 구멍이나 홈의 폭 대비 깊이입니다. 클수록 깊고 좁아서 식각이 어렵습니다.

메모리는 층을 높이 쌓을수록 용량이 커집니다. 3D 낸드 적층은 초기 24층에서 현 세대 321층까지 올라갔고, 채널 홀 종횡비는 100:1 이상, 최선단은 200:1에 이릅니다. 로직도 28nm에서 웨이퍼 한 장이 거치는 공정 단계가 약 350개였지만 2nm에서는 1,000개를 넘고, 전공정 기간은 약 8주에서 16주로 늘었습니다.

![공정 미세화가 이상 영향 범위를 키우는 과정](<contents/figures/s2-03.png>)

> **핵심.** 공정이 미세해질수록 한 번의 식각 이상이 미치는 **영향 범위가 커집니다.** 장비 상태의 작은 변화도 불량으로 이어지고, 단계와 기간이 늘어난 만큼 이상이 늦게 드러나며, 그 사이 같은 장비를 지난 웨이퍼가 모두 위험에 노출됩니다. 그래서 이상을 감지한 뒤 **얼마나 빨리, 정확히 조사하느냐**가 손실 규모를 좌우합니다.

### 2.3 이상(Excursion) 대응 프로세스 현황

이상 대응은 다섯 단계로 이루어집니다. 감지는 시스템이 자동으로 하지만, 그 뒤의 조사와 기록은 엔지니어가 직접 합니다.

![이상 대응 5단계와 자동화 수준](<contents/figures/s2-04.png>)

*파란색은 이미 자동화된 단계, 주황색은 TRACE가 맡는 수작업 단계입니다.*

### 2.4 인력 수급과 조사 업무의 문제

#### 국내 반도체 인력 수급 전망

*단위 만 명*

![국내 반도체 인력 수급 전망](<contents/figures/s2-05.png>)

<sub>한국반도체산업협회 (뉴데일리 2024.6)</sub>

#### 수작업 조사의 문제점

- 센서 기록, 레시피, 정비 이력, 매뉴얼이 서로 다른 시스템에 흩어져 있음
- 무엇과 비교할지 숙련자만 알아서 사람마다 결론이 다름
- 결론만 남고 근거가 빠져 다음 조사에서 재사용이 어려움
- 데이터 기반이 약한 조직은 데이터 추출·분석에 3배 이상 시간이 걸림 (McKinsey)

### 2.5 식각 공정을 먼저 선택한 이유

식각은 이상이 자주 생기고, 생겼을 때 손실이 크며, 조사에 쓸 데이터가 풍부하고, 시장이 이미 장비 관리에 큰 비용을 쓰고 있는 공정입니다. 여섯 가지 기준이 모두 겹치는 식각을 TRACE의 첫 적용 대상으로 정했습니다.

![식각 공정 선정 기준 6가지](<contents/figures/s2-06.png>)

*여섯 가지 기준이 모두 겹치는 공정이 식각입니다.*

### 2.6 식각 장비 시장의 성장 지표

식각은 노광·증착에 이어 세 번째로 큰 공정 장비 분야이며, 공정이 미세해질수록 웨이퍼 한 장에 들어가는 식각·증착 공정이 늘어납니다. Lam Research는 현 세대 대비 차세대에서 웨이퍼 1장당 식각·증착 시장이 파운드리·로직 2.0배, 낸드 1.8배, D램 1.7배로 커진다고 제시했습니다. 낸드 적층이 128층에서 5xx층으로 높아지고, 로직이 5nm에서 CFET 구조로, D램이 3D 구조로 넘어가며 식각 단계가 그만큼 많아지기 때문입니다.

장비를 판매한 뒤의 시장도 함께 커지고 있습니다. Lam의 고객 지원(CSBG) 매출은 2013년 약 $10억에서 2024년 약 $70억으로 연평균 17% 성장했고, 같은 기간 설치 장비 기반은 180% 이상 늘었습니다. 이미 설치된 식각 장비를 안정적으로 운영하고 이상에 빠르게 대응하는 일에 고객이 비용을 지불하고 있다는 뜻이며, TRACE는 이 설치 장비 운영 구간을 겨냥합니다.

#### 웨이퍼 1장당 식각·증착 시장 성장 배수

*Lam Research 제시 · 현 세대 대비 차세대*

![웨이퍼 1장당 식각·증착 시장 성장 배수](<contents/figures/s2-07.png>)

<sub>Lam Research 2025 Investor Day</sub>

#### Lam Research 고객 지원(CSBG) 매출

*단위 USD 억 · 설치 장비 관리 사업*

![Lam Research 고객 지원(CSBG) 매출](<contents/figures/s2-08.png>)

<sub>Lam Research 2025 Investor Day</sub>

### 2.7 식각 장비에 데이터·AI를 적용한 결과

식각 장비 1위 업체가 공개한 AI·데이터 기반 서비스 결과입니다. 장비 상태를 데이터로 관리할 때 얻는 효과가 이미 시장에서 확인되고 있습니다.

#### Lam Research AI·데이터 기반 서비스 성과

*단위 % · 회사 발표치*

![Lam Research AI·데이터 기반 서비스 성과](<contents/figures/s2-09.png>)

<sub>Lam Research 2025 Investor Day · 월 10만 장 웨이퍼 팹 기준 연 $1억 이상 운영비 절감 제시</sub>

> **정리.** 식각은 이상이 자주 생기고(반복·변동), 생겼을 때 손실이 크며(수율·고가 웨이퍼), 조사에 쓸 데이터가 풍부하고(센서), 시장이 이미 장비 관리에 돈을 쓰고 있는(설치 장비 서비스) 공정입니다. TRACE는 식각에서 먼저 검증한 뒤 같은 구조를 증착·CMP 등으로 넓힙니다.

---

<a id="s3"></a>

## 3. Excursion의 사업적 영향

### 3.1 Fab 매출 구성

공장의 매출은 세 가지 값의 곱으로 정해지고, 장비 이상은 이 중 두 가지를 직접 줄입니다.

![Fab 매출 구성](<contents/figures/s3-01.png>)

*맥킨지는 수율을 웨이퍼 가공 원가의 가장 중요한 단일 요인으로 인용합니다.*

### 3.2 조사 지연과 위험 노출 물량

조사가 끝나 판정이 내려지기 전까지 이상 장비를 지나간 웨이퍼는 모두 품질 위험에 노출됩니다(WIP at Risk). 조사 시간이 짧을수록 노출 물량이 줄어듭니다.

![조사 시간과 위험 노출 물량 개념도](<contents/figures/s3-02.png>)

*개념도입니다. 칸 하나는 이상 장비를 지나간 웨이퍼 묶음(Lot)이고, 주황색은 판정 전에 위험에 노출된 물량입니다.*

### 3.3 Excursion 비용 규모

#### 항목별 비용 규모

*단위 USD 천*

![항목별 비용 규모](<contents/figures/s3-03.png>)

<sub>Guru3D(China Times 보도, TSMC 미확인) · Edwards Vacuum(SemiEngineering 인용) · SemiEngineering</sub>

| 항목 | 수치 | 출처 |
|---|---|---|
| 2nm급 웨이퍼 단가 | 약 $30,000 / 장 | China Times 보도 인용(Guru3D 2025.6) |
| 2nm급 웨이퍼 1 Lot (25장) | 약 $750,000 | 위 단가 × 25장 |
| 첨단 공정 웨이퍼 가치 | $5,000 이상 / 장 | Edwards Vacuum, ASMC 2022 |
| 비계획 장비 정지 | 최대 약 $100,000 / 시간 | SemiEngineering |
| 중형 Fab 진공 장치 비계획 고장 1회 | 약 $150,000 | Edwards Vacuum, SEMICON West 2022 |
| 단일 제조사 8개 주요 공정 수율 손실 | 약 $6,800만 | McKinsey |

---

<a id="s4"></a>

## 4. 솔루션 제안

### 4.1 정의와 사용자

- **TRACE** (식각 공정 이상 조사 AI Agent): 반도체 식각 공정 이상 발생 시 과거 사례·계측 수치·SOP 근거를 자동으로 비교·연결해 엔지니어의 빠른 의사결정과 조사 기록 자산화까지 지원하는 AI Agent입니다.
- **최종 의사결정**: 장비 정지·Lot Hold·현장 조치와 보고서 승인은 엔지니어가 결정합니다. 기술팀 리더는 조사 이력을 열람해 재발 대응을 판단합니다.

![TRACE 사용자와 활용 방식](<contents/figures/s4-01.png>)

| 사용자 | 주요 업무 | TRACE 활용 |
|---|---|---|
| 작업자 | 장비 운전, 알람 1차 대응, 이상 현상 전달 | 채팅으로 이상 접수, 추가 질문 답변, 진행·결과 확인 |
| 식각 설비기술 엔지니어 | 알람 대응, 압력·가스·냉각 점검, PM·복구 | 사례·수치·문서를 대조해 점검 방향을 판단하고 보고서 승인 |
| 식각 공정기술 엔지니어 | Recipe/Step과 식각률·CD·균일도 검토 | 공정 조건·계측 결과로 설비 가설과 적용 조항을 공동 확인 |
| 기술팀 리더 | 반복 알람·조사 진행·인계 관리 | 승인 이력을 열람해 재발 대응 판단 |

### 4.2 B2B 연결 구조

반도체 제조사의 식각 조사는 이상 감지 이후 엔지니어가 데이터와 문서를 수작업으로 대조하는 데 시간이 걸립니다. 제안 팀은 고객사 사내망에 TRACE를 구축하고 기존 시스템을 MCP로 연결해, 엔지니어가 근거가 붙은 조사 초안을 검토·승인만 하도록 합니다.

![제안 팀, TRACE, 고객사, 관련 회사의 B2B 연결 구조](<contents/figures/s4-02.png>)

*제안 팀이 고객사 사내망에 TRACE를 구축·연동하고, 고객사 엔지니어가 조사 결과를 사용합니다. 외부 모델에는 계산된 요약값만 전달합니다.*

### 4.3 Pain Point와 제안 가치

알람 이후 조사를 현장 업무 단위로 나누면 다섯 단계이며, 단계마다 반복되는 병목이 있습니다.

![알람 이후 조사 5단계와 단계별 Pain Point](<contents/figures/s4-03.png>)

| 현장 문제 | 발생하는 일 | TRACE의 지원 방식 | 담당 Agent |
|---|---|---|---|
| **P1 문서 선정** | 장비·Step·개정본에 맞는 SOP/OCAP 조항을 찾고 Pumpdown과 Main Etch 문맥을 구분해야 함 | 장비·Step 조건으로 조항을 검색·재순위화하고 원문을 연결해 문서 선정 시간과 조건 오적용을 줄임 | 추천 Agent |
| **P2 계통 교차** | 압력·진공·가스·냉각 지침을 각각 확인해 필수 항목을 놓치기 쉬움 | 수치·센서·정비 관점을 순서대로 분석하고 PRS/VAC/GAS/TMP 연관 OCAP과 우선 확인 항목을 제시 | Run 비교·Sensor·추천 |
| **P3 과거 조치** | 조치 내용과 실제 해결·재발 결과가 분리되거나 누락됨 | 유사 사례와 승인 이력에서 조치와 결과를 분리하고, 과거 원인·조치는 확인 가설로 제시 | 범위 조사 Agent |
| **P4 PM 맥락** | 알람과 부품 교체·세정·재인증 이력을 따로 찾아야 함 | 최근 PM 종류·시점을 반영해 사례와 점검 순서를 정리 | Maintenance Agent |
| **P5 조사 기록** | 수치·문서·점검 결과가 메모와 대화에 흩어져 인계가 느림 | 출처가 붙은 보고서 초안을 만들고 수정 요청과 승인 스냅샷을 보존 | Report · Review |

### 4.4 다섯 단계 전문 조사

단순 질의응답 챗봇이 아니라, 전문 Agent 다섯이 순서대로 근거를 쌓아 한 보고서로 결합합니다. Business MCP로 사례·수치를 먼저 확보하고, 마지막에 RAG MCP로 문서 근거를 붙입니다.

1. **범위 조사.** 장비·Chamber·Recipe·증상으로 유사 사례와 권한 내 승인 이력을 조회하고 조사 범위를 정리합니다. 유사 사례가 없으면 근거 없이 결론을 내지 않고 조사를 종료합니다.
2. **Run 비교.** 사례 대비 입력 계측값의 평균·편차·z-score를 Python 도구로 계산하고 단위·사례 ID를 보존합니다.
3. **센서 관점 분석.** 압력·가스·냉각 등 계통별로 비교 결과를 해석하고 근거를 정리합니다.
4. **정비 관점 분석.** 최근 PM·부품 교체·세정 맥락과 과거 사례의 정비 조치를 비교합니다.
5. **점검 순서 추천.** 사례에 연결된 문서와 SOP 검색 조항을 원문에 연결해 원인 후보와 점검 순서를 제시합니다.

### 4.5 AI Agent가 필요한 이유

| 필요한 이유 | 설명 | 기대 효용 |
|---|---|---|
| 비정형 질문의 구조화 | 작업자의 자연어 보고에서 장비·Step·증상·계측값을 뽑아내고, 빠진 값만 골라 다시 묻습니다. | 접수 시간 단축, 재설명 감소 |
| 여러 관점의 순차 분석 | 사례·수치·센서·정비·문서 관점의 결과를 이어 붙여 하나의 판단 근거로 결합합니다. 고정 규칙이나 대시보드로는 관점 간 연결을 만들기 어렵습니다. | 계통별 확인 누락 감소 (P2) |
| 도구 선택과 근거 수집 | Agent가 상황에 맞는 조회·검색 도구와 검색어를 고르고, 한도 안에서 근거를 더 모읍니다. | 조사 품질 표준화 |
| 문서 해석과 연결 | 조사 결과에 맞는 SOP·OCAP 조항을 찾아 점검 순서로 연결하고 출처를 붙입니다. | 문서 선정 시간 단축 (P1) |
| 승인 기반 업무 변경 | 보고서 확정 저장은 Agent가 준비하고 엔지니어가 승인한 뒤에만 실행합니다. | 지식 자산화 (P3, P5) |

### 4.6 사용자 관점의 요청 흐름

작업자가 질문을 보내고 엔지니어가 승인하기까지, 화면에서 일어나는 일과 호출되는 API입니다.

![작업자와 엔지니어 관점의 API 요청 흐름](<contents/figures/s4-04.png>)

*실선은 사용자의 요청, 점선은 화면에 도착하는 응답과 SSE 이벤트입니다. 수정 요청(`revise`)을 보내면 TRACE는 분석을 다시 하지 않고 보고서만 고쳐 다시 검토를 요청합니다.*

### 4.7 역할 분담 (As-Is / To-Be)

![현행과 TRACE 도입 후 역할 분담 비교](<contents/figures/s4-05.png>)

*현행은 다섯 작업을 모두 엔지니어가 합니다. TRACE 도입 후 엔지니어는 점검 방향과 최종 현장 판단, 검토·승인을 맡습니다.*

### 4.8 현장 신뢰를 만드는 통제

![수치·근거·절차 3대 안전장치](<contents/figures/s4-06.png>)

| 통제 | 작동 방식 | 대응 Pain Point |
|---|---|---|
| 수치 신뢰 | 평균·편차·z-score 계산은 언어 모델이 아닌 `businessmcp`의 Python 도구가 수행하고, 단위와 사례 ID를 함께 남겨 수치 환각을 차단합니다. | P2, P5 |
| 근거 신뢰 | 모든 주장에 데이터 경로나 문서 출처를 붙이고, 벡터 검색과 AI 재순위화로 맞는 SOP 조항 원문을 연결합니다. 출처가 없는 주장은 보고서에 쓰지 않습니다. | P1, P2, P4 |
| 절차 신뢰 | 원인을 단정하지 않고 '확인 가설'로 제시하며, 엔지니어가 검토·승인한 보고서만 조직의 지식으로 축적·재활용합니다. | P3, P5 |

---

<a id="s5"></a>

## 5. 아키텍처

### 5.1 전체 구성도

![TRACE 아키텍처: 공개 요청 경로, 인증·내부 서비스·MCP 도구, 영속 데이터·문서](<contents/아키텍쳐.png>)

| 영역 | 구성 | 핵심 역할 |
|---|---|---|
| 01 공개 요청 경로 | Browser (Vue 3 SPA), Nginx · Web, FastAPI Backend, Agent (LangGraph), OpenAI | 화면 요청을 받아 Backend가 업무를 처리하고, Agent가 조사를 실행하며 필요할 때만 LLM을 호출 |
| 02 인증 · 내부 서비스 · MCP 도구 | Keycloak, Business MCP 도구 서버, RAG MCP 도구 서버 | 로그인·토큰 발급, 사례·통계·이력과 문서 근거를 표준 MCP 도구로 제공 |
| 03 영속 데이터 · 문서 | Keycloak 데이터, PostgreSQL · trace, SOP Knowledge Store | 인증 정보, 업무·조사 데이터, SOP·OCAP 원문과 색인을 분리 보관 |

### 5.2 서비스별 책임

| 서비스 | 책임 | 경계·통신 |
|---|---|---|
| Browser · Vue 3 SPA | 로그인 게이트, 이상 조사(질문·재질문 답변·진행·검토), 조사 기록·SOP 열람 | Nginx로만 HTTP 통신, 토큰을 요청에 포함 |
| Nginx · Web | Vue 빌드 결과 정적 제공, `/api` → Backend, `/auth` → Keycloak 프록시 | 유일한 공개 포트 |
| FastAPI · Backend | JWT 서명·issuer·audience 검증, 작업·메시지·검토·이벤트·SSE, 승인 스냅샷·이력·SOP API, Agent 실행·재개와 콜백 수신 | LLM 직접 호출 없음, 업무 규칙과 저장의 단일 지점 |
| Agent · LangGraph | 접수·재질문(interrupt/resume), 조사 Agent 5개 순차 실행, MCP 근거 수집·보고서 구성, 검토 대기·수정·승인 처리 | 업무 DB 직접 조회 없음, Backend와 HTTP 실행·콜백, Checkpoint만 PostgreSQL에 저장 |
| Business MCP 도구 서버 | 사례·승인 이력 조회, 통계 계산, 승인 이력 저장 | Backend `/internal/**` 경유 |
| RAG MCP 도구 서버 | 문서 ID 정확 조회, SOP·OCAP 의미 검색 | PostgreSQL·pgvector 문서 접근 |
| Keycloak | Authorization Code + PKCE, 로그인·갱신·로그아웃 | 가입 없음, 로그인 사용자 동일 권한 |
| OpenAI | 선택적 LLM 분석, SOP 임베딩·재순위화 | API Key가 없으면 제한적으로 동작 |

### 5.3 네트워크 경계와 배포

| 구역 | 포함 서비스 | 허용 통신 |
|---|---|---|
| 공개 | Nginx · Web | 브라우저 → 정적 웹, `/api`(SSE 포함), `/auth` |
| 내부 (서비스) | FastAPI Backend, Agent, Business MCP, RAG MCP, Keycloak | Docker 내부 네트워크에서만 상호 호출, 호스트 포트 미공개, 내부 호출은 공유 키로 보호 |
| 내부 (데이터) | PostgreSQL · trace, SOP Knowledge Store(sop-postgres), Keycloak 데이터 | 서비스별 소유 영역 분리, 필요한 서비스만 접근 |
| 외부 아웃바운드 | OpenAI API | Agent와 RAG MCP만 호출, 공정 원천 데이터 대신 계산된 요약값만 전송 |

전체 서비스는 Docker Compose 한 구성으로 배포하고, 사내망 설치 시 같은 구성을 고객 서버로 옮깁니다. Backend는 LLM을 직접 호출하지 않아, 외부 모델 연결은 Agent와 RAG MCP 두 곳으로만 한정됩니다.

### 5.4 요청 경로: 동기 처리와 202·SSE 처리

짧은 업무 요청은 동기로 응답하고, 수십 초가 걸리는 AI 조사는 즉시 `202`와 `taskId`를 돌려준 뒤 Backend가 Agent를 HTTP로 실행하고 진행 상황을 SSE로 보냅니다.

![동기 경로와 202·SSE 비동기 경로 순서도](<contents/figures/s5-01.png>)

*실선은 요청, 점선 화살표는 응답과 SSE입니다. 조사 실행 중에도 화면은 같은 taskId로 진행을 받아 봅니다.*

| 구분 | 대상 요청 | 응답 방식 |
|---|---|---|
| 동기 | 조사 목록·상세 조회, 승인 이력 조회, SOP 원문 조회 | `200` 즉시 응답 |
| 비동기 접수 | 조사 생성, 재질문 답변, 검토(승인·수정 요청) | `202` + `taskId`, 이후 Backend가 Agent를 HTTP로 실행·재개 |
| 진행 전달 | 도구 실행, 재질문, 승인 요청, 완료·실패 | Agent 콜백 → Backend 저장 → SSE 이벤트, 재연결 시 순번 이후부터 이어 받기 |

### 5.5 문서 색인·검색·출처 경로

![문서 색인과 검색, 출처 반환 경로](<contents/figures/s5-02.png>)

| 단계 | 내용 |
|---|---|
| 색인 | SOP Knowledge Store의 `sop-ocap/` 원문(SOP 3종, OCAP 19종)을 절 단위로 나누고 문서 ID·제목·버전·개정일·Step·계통 코드(PRS/VAC/GAS/TMP 등)를 붙여 `text-embedding-3-small`로 벡터화해 sop-postgres(pgvector)에 저장합니다. 문서 내용 해시가 같으면 재임베딩하지 않습니다. |
| 검색 | RAG MCP가 질의를 같은 모델로 벡터화하고 Step·문서 유형 메타 필터를 먼저 적용한 뒤 유사도 상위 20건을 뽑아 LLM 재순위화로 3건을 고릅니다. 사례에 연결된 문서는 PostgreSQL · trace의 `etch_documents`에서 ID로 정확 조회합니다. |
| 출처 반환 | 모든 결과에 `doc_id`, 제목, 버전, 조항 번호, 발췌문, 점수, 원문 URI를 담습니다. 보고서는 출처 ID가 있는 문장만 근거로 씁니다. |
| 원문 열람 | 화면의 출처 링크는 Backend SOP API가 원문을 조회해 보여 주고, Agent는 RAG MCP Resource로 같은 원문을 읽습니다. 색인·검색은 RAG MCP만 맡습니다. |

### 5.6 변경 승인·상태 저장·재개 흐름

![변경 도구 승인과 상태 저장, 재개 순서도](<contents/figures/s5-03.png>)

*승인 지점은 두 곳입니다. Backend가 승인 요청의 사용자 신원을 확인·기록하고, 확정 저장 요청이 들어올 때 승인 ID를 다시 확인합니다.*

1. **멈춤.** Approval Required Node가 초안과 근거, 실행할 변경 Tool·인자를 저장하고 Review Node의 `interrupt()`에서 멈춥니다. 상태는 `thread_id = taskId`로 PostgreSQL · trace에 Checkpoint로 저장됩니다.
2. **검토.** Backend는 Agent 콜백을 받아 상태를 `WAITING_APPROVAL`로 바꾸고, 검토 화면에 보고서와 도구·인자를 보여 줍니다.
3. **결정.** 승인 또는 수정 요청을 받으면 Backend가 JWT로 사용자를 확인해 승인자·시각을 기록하고 승인 ID를 발급한 뒤 Agent에 HTTP로 재개를 요청합니다.
4. **재개.** Agent가 같은 thread의 Checkpoint에서 `Command(resume=…)`로 이어 실행합니다. 승인 시에만 변경 Tool을 호출하고, 수정 요청은 분석을 다시 실행하지 않고 의견을 반영해 보고서만 다시 작성합니다.
5. **확정.** Business MCP는 Backend `/internal/**`로 승인 이력 저장을 요청하고, Backend는 승인 ID와 대상 작업이 일치할 때만 승인 스냅샷을 저장합니다.

### 5.7 데이터 계층 분리

| 저장소 | 저장 데이터 | 쓰기 | 읽기 |
|---|---|---|---|
| Keycloak 데이터 | dev-file + keycloak_data: Realm, 기본 계정, 세션 | Keycloak | Keycloak |
| PostgreSQL · trace | v1 작업·메시지·이벤트·검토·승인 이력, 샘플 사례·`etch_documents`, LangGraph 체크포인트 | Backend, Agent (체크포인트), 샘플 적재 | Backend, Business MCP (Backend 경유), RAG MCP (문서 ID 조회) |
| SOP Knowledge Store | `sop-ocap/` SOP 3종 + OCAP 19종 원문, sop-postgres·pgvector 절 단위 색인 | 색인 배치 | Backend (원문 조회), RAG MCP (색인·검색) |

PostgreSQL · trace 안에서도 작업·이력, 샘플 사례·문서, 체크포인트를 서비스별 소유 영역으로 나눕니다. 인증 정보는 Keycloak 데이터에만 두어 Agent와 MCP 도구가 사용자 계정 정보를 읽지 않습니다.

### 5.8 품질 특성 대응 (ISO/IEC 25010)

| 품질 특성 | 요구 | 대응 |
|---|---|---|
| 성능 효율성 | 조회 응답 지연 최소화, 긴 AI 작업이 요청 스레드를 점유하지 않음 | 동기 조회는 Backend가 바로 응답, AI 조사는 `202` 후 Agent를 별도로 실행, 조사 1건 최대 8턴·120초, SSE로 체감 대기 단축 |
| 신뢰성 | 장애 시 작업 유실 없이 재개, 외부 모델 장애에도 서비스 유지 | Node 단위 Checkpoint와 interrupt/resume, 명령 ID로 이전 명령의 지연 콜백 차단, 실패 상태 명시, OpenAI API Key가 없어도 제한적으로 동작 |
| 보안 | 기밀성·무결성·책임 추적성·인증 | Keycloak PKCE 로그인과 Backend의 JWT 서명·issuer·audience 검증, 공개 포트 1개, Backend의 LLM 직접 호출 없음, 변경은 승인 ID 이중 확인, 승인 스냅샷·이벤트 보존 |
| 기능 적합성 | 정확한 수치와 근거 | 수치는 Python 도구만 계산, 출처 없는 주장은 보고서에서 제외, 유사 사례가 없으면 조사 종료 |
| 호환성 | 고객사 시스템과의 상호 운용 | MCP 표준 인터페이스와 Streamable HTTP, 데이터 소스별 Tool 교체 |
| 유지보수성 | 변경 영향 최소화 | 서비스별 책임과 데이터 소유 영역 분리, Instructions·Tool 스키마 버전 관리, 평가 질문 세트로 회귀 확인 |
| 사용성 | 현장 사용자가 진행과 근거를 바로 이해 | 로그인 게이트 뒤 단일 화면 흐름, 단계별 진행 이벤트, 출처 링크와 원문 열람, 승인 전 도구·인자 표시 |

---

<a id="s6"></a>

## 6. AI Agent 설계

### 6.1 Agent State

| 필드 | 타입 | 내용 | 갱신 Node |
|---|---|---|---|
| `task_id` · `trace_id` | UUID · str | 작업 ID(= Checkpoint thread_id), 관측용 추적 ID | 생성 시 |
| `requester` | {user_id, name} | 로그인 사용자 신원. 모델 입력에서 제외하고 Tool 인자로만 주입 | 생성 시 |
| `question` · `messages` | str · list[Message] | 원문 질문과 재질문을 포함한 대화 | Intake, Clarify |
| `context` | RunContext | 장비·Chamber·Recipe·Step·증상·입력 계측값·최근 PM | Intake, Clarify |
| `missing_fields` · `clarifications` | list[str] · int | 조사에 필요한데 빠진 필드, 재질문 횟수 | Intake |
| `scored_cases` | list[ScoredCase] | 유사 사례와 유사도 점수 | 범위 조사 Agent |
| `investigations` | list[InvestigationSummary] | 권한 내 과거 승인 조사 이력 | 범위 조사 Agent |
| `comparison` | MetricAnalysis | 평균·편차·z-score 비교 결과와 단위 | Run 비교 Agent |
| `stages` | list[StageResult] | 전문 Agent별 분석 결과와 근거 ID | 각 전문 Agent |
| `documents` | list[Document] | 문서 근거와 출처(doc_id·조항·버전·URI) | 추천 Agent |
| `tool_calls` · `tool_results` | list[ToolCall] · list[ToolResult] | 모델이 선택한 도구·인자·상태·지연, 결과 또는 구조화된 오류 | 전문 Agent |
| `report` | Report | 요약, 단계별 결과, 원인 후보(확인 가설), 점검 순서, 근거 목록 | Report |
| `pending_action` | {tool, args} | 승인 대기 중인 변경 Tool과 인자 | Approval Required |
| `review` · `feedback` | {action, comment, reviewer_id, approval_id} · list[str] | approve · revise 결정과 누적 수정 의견 | Review |
| `budget` | {turns, started_at, tool_counts} | 턴 수, 경과 시간, 도구별 호출 횟수 | 전문 Agent |
| `final_status` | enum | DONE · INCOMPLETE · FAILED | 종료 Node |

### 6.2 LangGraph 실행 흐름

![TRACE Agent LangGraph 실행 흐름: 접수·정보 보완, 근거 수집·순차 분석, 보고서·엔지니어 검토](<contents/Agent Graph.png>)

| Node | 역할 | 도구 · 이벤트 |
|---|---|---|
| Intake | 질문을 구조화하고 장비·Chamber·Recipe·증상 필드를 추출 | - |
| Question Event | 누락 필드를 안내하는 재질문 생성 (최대 3회) | `QUESTION` |
| Clarify · interrupt | 작업자 답변 대기, Checkpoint에서 중단·재개 후 필수 정보 재판단 | `RESUMED` |
| 범위 조사 Agent | 유사 사례·승인 이력 조회, 조사 범위 정리 | `search_cases`, `list_investigations` · `SEARCH_STARTED` |
| Run 비교 Agent | 평균·편차·z-score 정량 비교 결과 작성 | `analyze_metrics` · `ANALYSIS_STARTED` |
| Sensor Agent | 센서 관점에서 비교 결과와 사례 근거 분석 | 수집 근거 사용 |
| Maintenance Agent | 정비 관점에서 PM·부품·조치 이력 분석 | 수집 근거 사용 |
| 추천 Agent | 원인 후보와 점검 순서 정리, 문서 근거 수집 | `search_documents`, `search_sop` |
| Report | 단계 결과·사례·문서를 보고서로 조립 | `REPORT_STARTED` |
| Approval Required | 초안·근거 저장, 변경 Tool 준비, 검토 요청 | `APPROVAL_REQUIRED` |
| Review · interrupt | 엔지니어 검토 대기 (approve · revise) | - |
| DONE | 승인 스냅샷·이력 확정 저장 | `save_investigation` · `DONE` |
| INCOMPLETE | 정보 부족 또는 유사 사례 없음으로 종료 | `INCOMPLETE` |

### 6.3 조회 도구와 변경 도구의 실행 조건

| 구분 | 조회 도구 | 변경 도구 |
|---|---|---|
| 대상 | `search_cases`, `list_investigations`, `get_investigation`, `analyze_metrics`, `search_documents`, `search_sop` | `save_investigation` |
| 모델 노출 | 전문 Agent별 허용 목록만 모델에 바인딩 | 모델에 바인딩하지 않음. Approval Required Node가 `pending_action`으로만 준비 |
| 실행 시점 | 조사 중 언제든, Agent Loop 한도 안 | 엔지니어 승인 후 DONE Node에서만 |
| 권한 | 로그인 사용자 범위의 데이터 (신원은 Harness가 주입) | 승인 ID 필수, Backend가 승인자·대상 작업 재확인 |
| 실패 처리 | 오류를 모델에 돌려주고 대안 도구 선택 | 재시도 후에도 실패하면 FAILED, 승인 상태는 유지해 재처리 |

---

<a id="s7"></a>

## 7. MCP Server 설계

### 7.1 서버 구성과 연결

Agent는 업무 DB에 직접 접속하지 않고 두 MCP Server의 Tool·Resource로만 근거를 읽고 변경을 요청합니다. 사례·이력·통계는 `businessmcp`가 먼저, 문서·출처는 `ragmcp`가 나중에 맡아 고객사 시스템이 달라도 서버 단위로 교체해 연결합니다.

| 서버 | 제공 기능 | 연결 | 접근 저장소 |
|---|---|---|---|
| `businessmcp` | 조회 Tool 4종, 변경 Tool 1종 | Streamable HTTP · `http://businessmcp:8001/mcp` | Backend `/internal/**` 경유 (PostgreSQL · trace) |
| `ragmcp` | 검색 Tool 2종, 원문 Resource 2종, Prompt 1종 | Streamable HTTP · `http://ragmcp:8002/mcp` | PostgreSQL · trace(`etch_documents`), sop-postgres·pgvector, OpenAI Embedding |

### 7.2 businessmcp Tool

| Tool | 구분 | 설명 | 입력 | 반환 |
|---|---|---|---|---|
| `search_cases` | 조회 | 장비·Chamber·Recipe·Step·증상으로 유사 사례를 찾아 유사도 점수와 함께 반환합니다. | `context: RunContext` {equipment_id, chamber?, recipe?, step?, symptom, metrics?}, `limit: int = 5` | `list[ScoredCase]` {case_id, score, recipe, step, symptom, metrics, cause, action, outcome, document_ids, source} |
| `analyze_metrics` | 조회 | 선택한 사례 대비 입력 계측값의 평균·편차·z-score를 계산합니다. | `case_ids: list[str]`, `metrics: dict[str, float]` | `MetricAnalysis` {rows[{metric, unit, value, ref_mean, ref_std, z_score, n}], case_ids, method} |
| `list_investigations` | 조회 | 과거 승인 조사 이력을 장비·증상 조건으로 조회합니다. | `equipment_id?: str`, `symptom?: str`, `limit: int = 5` (요청자 신원은 Harness가 주입) | `list[InvestigationSummary]` {task_id, approved_at, hypotheses, actions, outcome} |
| `get_investigation` | 조회 | 승인 조사 1건의 보고서와 근거를 조회합니다. | `task_id: UUID` | `Investigation` {report, evidence, approved_by, approved_at} |
| `save_investigation` | 변경 | 엔지니어가 승인한 조사 보고서를 Backend 내부 엔드포인트로 확정 저장합니다. | `task_id: UUID`, `approval_id: str`, `report: Report` | {investigation_id, version, saved_at} |

<sub>파란 행은 변경 Tool입니다. Business MCP의 모든 Tool은 DB에 직접 접근하지 않고 Backend `/internal/**` 엔드포인트를 호출하며, 변경 Tool의 경우 Backend가 승인 ID·대상 작업·승인자를 다시 확인합니다.</sub>

### 7.3 ragmcp Tool · Resource · Prompt

| 종류 | 이름 | 설명 | 입력 → 반환 |
|---|---|---|---|
| Tool | `search_documents` | 유사 사례가 참조하는 문서·조항을 `etch_documents`에서 ID로 정확히 조회합니다. | `document_ids: list[str]` → `list[Document]` {doc_id, title, version, clause_id, text, uri} |
| Tool | `search_sop` | 질의를 벡터화해 장비·Step·문서 유형으로 거른 뒤 후보 20건 중 재순위화한 SOP/OCAP 조항을 출처와 함께 반환합니다. | `query: str`, `equipment?: str`, `step?: str`, `doc_types?: list["SOP"\|"OCAP"\|"WI"\|"MANUAL"]`, `top_k: int = 3` → `list[DocHit]` {doc_id, title, version, revised_at, clause_id, section, snippet, score, uri} |
| Resource | `doc://{doc_id}` | 문서 원문 전체 (`text/markdown`) | Agent 원문 확인 |
| Resource | `doc://{doc_id}/clauses/{clause_id}` | 조항 단위 원문 | 보고서 출처 링크 |
| Prompt | `investigation_report` | 보고서 형식과 인용 규칙 템플릿 | Report Node |

### 7.4 오류 계약

Tool은 실패 시 예외 대신 구조화된 오류를 돌려줍니다. 형식은 `{"code", "message", "retryable", "hint", "details"}`이며, Harness는 `retryable`로 재시도 여부를 정하고 `hint`를 모델에 전달해 다음 호출을 고치게 합니다.

| code | 의미 | 재시도 | hint로 전달할 정보 |
|---|---|---|---|
| `INVALID_ARGUMENT` | 입력 형식·값 오류 | 아니오 | 잘못된 필드와 허용 값 |
| `NOT_FOUND` | 장비·사례·문서 없음 | 아니오 | 가까운 후보 (같은 장비의 다른 Chamber 등) |
| `INSUFFICIENT_DATA` | 통계 계산에 필요한 사례 수 부족 | 아니오 | 확보 건수, 완화 가능한 조건 |
| `PERMISSION_DENIED` | 요청자 권한 밖 데이터 | 아니오 | 필요한 역할 |
| `APPROVAL_REQUIRED` | 승인 ID 없음 또는 불일치 | 아니오 | 현재 승인 상태 |
| `UPSTREAM_TIMEOUT` | DB·임베딩 응답 지연 | 예 | 권장 대기 시간 |
| `UPSTREAM_UNAVAILABLE` | Backend·DB 연결 실패 | 예 | 권장 대기 시간 |

### 7.5 MCP Client 연결

1. **연결.** Agent 기동 시 MCP Client가 두 서버에 Streamable HTTP로 연결합니다. 요청 헤더에 내부 공유 키와 Trace ID를 넣습니다.
2. **발견.** `list_tools`·`list_resources`·`list_prompts`로 목록을 받아 Harness의 허용 목록·스키마와 대조하고, 일치하는 Tool만 LangChain Tool로 변환합니다.
3. **바인딩.** 범위 조사 Agent에는 `search_cases`·`list_investigations`, Run 비교 Agent에는 `analyze_metrics`, 추천 Agent에는 `search_documents`·`search_sop`만 바인딩합니다. 변경 Tool은 DONE Node에서 직접 호출합니다.
4. **상태 확인.** 두 서버 중 하나라도 연결되지 않으면 Agent는 준비 상태를 내려 새 실행 요청을 받지 않고, Backend는 해당 작업을 실패 사유와 함께 표시합니다. 연결이 돌아오면 같은 thread로 다시 실행할 수 있습니다.

---

<a id="s8"></a>

## 8. AI Agent 구현 설계

### 8.1 구현 항목

| 요구 | 구현 방식 | 확인 방법 |
|---|---|---|
| State·Graph 반영 | 6.1 State를 Pydantic 모델로 정의하고, 6.2 Node·분기를 `StateGraph`에 1:1로 등록해 Checkpointer와 함께 compile. 전문 Agent는 각각 하위 Graph로 구성 | Graph 구조 출력과 실행 흐름도 대조 |
| 모델의 Tool 선택 | gpt-5.4-mini에 전문 Agent별 허용 MCP Tool을 바인딩하고, 모델이 고른 Tool과 인자를 Harness 검사 후 MCP로 실행 | 평가 질문별 선택 Tool 기록 |
| 근거 기반 답변 | 보고서는 구조화 출력(요약·단계 결과·원인 후보·점검 순서·근거 ID)으로 받고, 근거 ID가 State의 사례·통계·문서에 없으면 해당 문장을 제외 | 인용 ID 유효성 검사 |
| Checkpointer·재개 | PostgreSQL Checkpointer를 조사 운영 DB에 두고 `thread_id = taskId`로 저장, Clarify·Review Node의 `interrupt()`에서 멈춘 뒤 `Command(resume)`로 재개 | 승인 대기 중 Agent 재시작 후 재개 |
| 이벤트 발행 | Node·Tool 콜백에서 Backend 내부 콜백 엔드포인트로 전송, Backend가 작업별 순번(seq)을 붙여 저장·SSE 송출 | SSE 이벤트 순서·중복 확인 |

### 8.2 이벤트 정의

모든 이벤트는 `seq`, `task_id`, `trace_id`, `type`, `ts`, `payload`를 가집니다.

| type | 발생 시점 | payload |
|---|---|---|
| `TASK_ACCEPTED` | 조사 생성 직후 | 상태 QUEUED, 요청자 |
| `QUESTION` · `RESUMED` | 재질문, 답변 후 재개 | 누락 필드와 질문 문장 / 재개 사유 |
| `SEARCH_STARTED` | 범위 조사 Agent 시작 | 추출된 조사 조건 |
| `ANALYSIS_STARTED` | Run 비교 Agent 시작 | 비교 대상 사례 수 |
| `TOOL_STARTED` · `TOOL_FINISHED` · `TOOL_FAILED` | Tool 호출 전후 | 서버·Tool·인자 요약, 지연, 결과 요약 또는 오류 code |
| `REPORT_STARTED` | Report Node 시작 | 단계별 결과 요약 |
| `APPROVAL_REQUIRED` | Approval Required Node | 변경 Tool 이름·인자, 보고서 스냅샷 |
| `DONE` · `INCOMPLETE` · `FAILED` | 종료 | 최종 상태, 확정 저장 ID 또는 사유 |

---

<a id="s9"></a>

## 9. Harness 설계

### 9.1 통제 항목

| 항목 | 설계 | 통제 지점 |
|---|---|---|
| Instructions | 역할(식각 이상 조사 보조), 도구 사용 규칙(수치는 Tool 결과만 인용, 문서 주장에는 출처 ID), 금지 사항(원인 단정, 숫자 생성, 출처 없는 조치 권고), 출력 형식(보고서 스키마)을 파일로 버전 관리하고 Trace에 버전을 기록 | 모든 모델 호출 |
| Tools | 모델의 Tool 호출을 허용 목록·입력 스키마로 검사한 뒤 MCP로 실행하고, 결과는 요약·근거 ID로, 오류는 code·hint로 모델에 전달 | 전문 Agent의 도구 실행 |
| Context | 대화 원문 대신 State 요약(조사 조건·앞 단계 결과·확보 근거)을 다음 Agent 입력으로 쓰고, 문서 발췌 길이와 근거 개수를 제한, 입력 토큰 예산을 넘으면 오래된 대화부터 요약 | 각 모델 호출 직전 |
| State·Memory | Node 단위 Checkpoint로 작업 상태를 저장·복원, 같은 장비의 승인 조사 이력은 `list_investigations`로만 장기 기억처럼 사용 | 조사 운영 DB |
| Agent Loop | 조사 전체 최대 8턴·120초, 같은 Tool·같은 인자 2회까지, 재질문 3회. 한도를 넘으면 INCOMPLETE로 종료 | 전문 Agent, Clarify |
| Guardrails | 변경 Tool은 모델에 노출하지 않고 승인 후에만 실행, 승인자 신원은 Backend가 확인·기록. 사용자 이름·사번은 모델 입력에서 가명화하고, 공정 원천 데이터는 계산된 요약값만 외부 모델로 전송. 문서·이력 내용은 지시가 아닌 데이터로 취급 | Approval Required, DONE |
| Recovery | 모델 429·5xx·타임아웃은 지수 백오프로 2회 재시도, `retryable` Tool 오류는 1회 재시도, 이후 실패는 모델에 전달하거나 FAILED 처리. OpenAI API Key가 없거나 모델이 응답하지 않으면 LLM 분석을 줄인 제한 모드로 동작하고, 실패한 작업은 같은 thread로 재실행 | 모델·도구 호출 래퍼 |
| Observability | Backend가 발급한 Trace ID를 Agent 실행 요청·콜백·MCP 요청 헤더로 전파하고, 모델·Node·Tool별 지연, 입력·출력 Token, 단가 기준 비용을 기록 | 콜백 핸들러, Trace 저장소 |

### 9.2 평가 질문 세트

| 유형 | 예시 질문 | 기대 동작 | 판정 기준 |
|---|---|---|---|
| 정비 맥락 | "PM 후 He 후면 압력 저하 알람이 반복돼요." | 유사 사례·승인 이력 조회, Maintenance Agent의 PM 맥락 분석, 냉각 OCAP 조항 추천 | 필수 Tool 호출 |
| 수치 비교 | "Main Etch 압력이 85 mTorr까지 올랐어요." | 사례 대비 평균·편차·z-score 계산 | 계산값이 Tool 결과와 일치 |
| 문맥 구분 | "공정 시작 전 Pumpdown Timeout이에요." | 진공·누설 조항 우선, Main Etch 압력 제어 조항 제외 | 부적합 조항 0건 |
| 정보 누락 | "장비가 이상해요." | 장비·증상 재질문, 3회 초과 시 INCOMPLETE | 재질문 필드 정확 |
| 사례 없음 | 데이터에 없는 장비·알람 | 유사 사례 없음으로 INCOMPLETE | 원인 단정 0건 |
| 과거 조치 | "지난번 같은 알람 조치가 해결됐나요?" | 조치와 결과(해결·재발)를 분리해 제시 | 허위 해결 단정 0건 |
| 변경 승인 | 보고서 생성 후 | 승인 전 멈춤, 승인 후 같은 thread에서 저장 | 승인 전 저장 0건 |
| 수정 요청 | "점검 순서 표현을 더 구체적으로" | 분석 재실행 없이 보고서만 재작성 | Tool 재호출 0건 |
| 도구 오류 | MCP 타임아웃 주입 | 재시도 후 복구 또는 실패 명시 | FAILED 사유 기록 |

1. **기준선 측정.** 현재 설정(Instructions 버전, 모델, 검색 top_k, Loop 한도)으로 평가 세트를 실행하고 결과를 Trace와 함께 저장합니다.
2. **변경 후 측정.** 설정을 하나씩 바꿔 같은 세트를 다시 실행합니다.
3. **비교.** Tool 선택 정확도, 수치 일치율, 출처 포함률, INCOMPLETE 판단 정확도, 평균 턴 수·지연·Token·비용을 비교해 채택 여부를 정합니다.

---

<a id="s10"></a>

## 10. 화면·업무 API·인증

### 10.1 화면 구성

| 화면 | 주요 기능 |
|---|---|
| 로그인 게이트 | Keycloak 로그인·토큰 갱신·로그아웃. 로그인 전에는 다른 화면에 접근할 수 없음 |
| 이상 조사 | 이상 현상 채팅 접수, 재질문 답변, 진행 타임라인, 근거·출처 검토, 승인·수정 요청 |
| 조사 기록 | 승인된 조사 이력과 보고서 스냅샷, 승인자·시각 열람 |
| SOP | SOP 3종·OCAP 19종 원문 열람, 보고서 출처 링크에서 해당 조항으로 이동 |

### 10.2 구현 화면

로그인한 사용자가 이상을 접수하고, 조사 결과와 근거를 확인하고, 지난 조사와 SOP 원문을 찾아보는 화면입니다.

#### ① 이상 조사

*질문을 보내면 왼쪽에 에이전트 흐름이 단계별로 진행되고, 가운데에 비교 수치(평균 대비 편차·z-score)와 전문 Agent별 조사 결과가, 오른쪽에 관련 SOP·OCAP 조항이 조사 근거로 표시됩니다.*

![이상 조사 화면: 에이전트 흐름, 분석 결과, 조사 근거 패널](<contents/image (2).png>)

#### ② 조사 기록

*서버에 저장된 조사를 상태(완료·근거 부족)와 함께 나열하고, 선택한 조사의 요약·비교 수치·단계별 결과와 근거를 다시 보거나 이어서 진행합니다.*

![조사 기록 화면: 조사 목록, 선택한 조사 상세, 조사 근거 패널](<contents/image (1).png>)

#### ③ SOP 목록

*SOP·OCAP 22개 문서를 문서명·번호·키워드로 검색하고, 버전·최근 개정·담당 팀과 함께 원문을 열람합니다. 보고서의 출처 링크도 이 화면의 해당 조항으로 연결됩니다.*

![SOP 목록 화면: 문서 검색과 목록, 선택한 문서 원문](<contents/image.png>)

#### ④ 로그인

*Keycloak 로그인 화면입니다. 로그인하지 않으면 다른 화면에 접근할 수 없고, 로그인 후 토큰으로 모든 API를 호출합니다 (10.5).*

![TRACE Keycloak 로그인 화면](<contents/image (3).png>)

### 10.3 작업 API

| 요청 | 설명 | 응답 |
|---|---|---|
| `POST /api/tasks` | 질문으로 조사 생성, Agent 실행 요청 | `202` {taskId} |
| `GET /api/tasks` | 조사 목록 | `200` |
| `GET /api/tasks/{id}` | 상세: 대화, 보고서, 근거·출처 | `200` |
| `GET /api/tasks/{id}/events` | SSE 구독, 마지막 순번 이후 이벤트 재생 | `text/event-stream` |
| `POST /api/tasks/{id}/messages` | 재질문 답변, Agent 재개 요청 | `202` |
| `GET /api/tasks/{id}/approval` | 승인 대기 중인 변경 Tool·인자, 보고서 스냅샷 | `200` |
| `POST /api/tasks/{id}/review` | 승인·수정 요청 {action: approve · revise, comment} | `202` |
| `GET /api/investigations` | 승인 조사 이력 목록·상세 | `200` |
| `GET /api/sop/{docId}` | SOP·OCAP 원문 조회 | `200` |

<sub>내부 API(Agent 실행·재개, Agent 진행 콜백, Business MCP용 `/internal/**`)는 Nginx 경로에 노출하지 않고 내부 공유 키로만 호출합니다.</sub>

### 10.4 진행·근거·승인 표시

- **진행.** SSE 이벤트를 타임라인으로 보여 줍니다. 범위 조사 → Run 비교 → Sensor → Maintenance → 추천 단계를 순서대로 표시하고, 도구 실행은 "유사 사례 조회 중 → 5건 확인"처럼 Tool과 결과 요약을, 재질문은 입력창을, 실패는 사유를 보여 줍니다.
- **근거.** 보고서 문장마다 근거 칩을 붙입니다. 데이터 근거는 값·단위·사례 ID, 문서 근거는 문서명·버전·조항을 보여 주고 누르면 SOP 원문을 엽니다.
- **승인.** 검토 화면에 실행 예정 변경 Tool 이름과 인자(저장 대상 작업, 보고서 버전)를 그대로 보여 주고 승인·수정 요청 버튼과 의견 입력을 둡니다. 승인 후에는 승인자·시각이 남습니다.

### 10.5 인증과 권한

1. **로그인.** 화면은 Nginx `/auth`를 거쳐 Keycloak에 Authorization Code + PKCE로 로그인하고 토큰을 받습니다. 토큰 갱신과 로그아웃도 Keycloak이 처리합니다.
2. **검증.** Backend가 Keycloak 공개키(JWKS)로 JWT의 서명·issuer·audience·만료를 검증하고, 검증에 실패한 요청은 거부합니다.
3. **권한.** 별도 가입 절차 없이 Keycloak에 등록된 사용자만 로그인하며, 로그인 사용자는 같은 권한으로 조사·검토·승인을 할 수 있습니다.
4. **책임 기록.** 조사 생성·답변·승인·수정 요청마다 토큰의 사용자 신원을 이벤트와 승인 스냅샷에 남겨, 누가 무엇을 승인했는지 추적합니다.

> **확장.** 작업자·엔지니어·관리자 역할 구분과 담당 장비 기준 배정은 고객사 계정 체계와 연동하는 단계에서 Keycloak 역할과 Backend 권한 검사로 추가합니다 (15장).

---

<a id="s11"></a>

## 11. 기대 효과 및 KPI

### 11.1 Value Driver

| 효과 | 작동 방식 | 수혜 조직 | Pain Point |
|---|---|---|---|
| 조사 시간 단축 | 사례 탐색·수치 비교·SOP 조항 확인 자동화 | 설비·공정 기술 | P1, P2 |
| 손실 범위 축소 | 판정 시점이 앞당겨져 Lot Hold·장비 정지·위험 노출 물량 감소 | 생산·Fab 운영 | - |
| 조사 품질 표준화 | 5단계 전문 조사 순서와 보고서 형식을 Graph로 고정해 계통별 확인 누락 감소 | 기술 조직 전반 | P2 |
| 해결 여부 오인 방지 | 과거 조치와 결과를 분리하고 검증되지 않은 조치를 해결로 단정하지 않음 | 설비 기술, 기술팀 리더 | P3 |
| 지식 자산화 | 엔지니어가 승인한 조사 이력을 다음 조사에서 권한 범위 내 재사용 | 기술 조직, 교육 | P3, P5 |
| 인계·품질 대응 효율 | 수치·사례 ID·문서 출처·승인자 기록으로 인수인계와 고객 품질 문의·8D 대응 | 기술팀 리더, 품질보증 | P5 |

### 11.2 운영 KPI

| KPI | 정의 | 측정 시점 |
|---|---|---|
| MTTI | 조사 요청부터 승인 가능한 보고서 생성까지 평균 시간 | PoC, Pilot |
| 엔지니어 투입 공수 | 조사 1건당 엔지니어 작업 시간과 시스템 조작 수 | PoC, Pilot |
| Lot Hold 시간 | 조사 연계 보류 건의 평균 보류 시간 | Pilot |
| 수치·근거 정합성 | 보고서 수치와 Tool 계산값 일치율, 주장–출처 ID 대응률 | PoC, Pilot |
| 승인 통제 준수 | 승인 전 확정 저장 건수 (목표 0건) | 상시 |

> **측정 원칙.** 효과는 고객사 Pilot에서 현행 조사 시간·공수를 기준선으로 먼저 측정한 뒤 같은 지표로 비교합니다. Agent 품질은 9.2의 평가 질문 세트로 설정 변경 전후를 비교합니다. 이 기획서는 측정 전 효과 수치를 제시하지 않습니다.

---

<a id="s12"></a>

## 12. 시장 사례로 본 효과

제조 데이터와 AI를 업무에 적용한 기업·기관이 공개한 결과입니다(식각 장비 사례는 3.3 참고). 모두 각 회사·기관의 발표치입니다.

#### 공개된 개선 폭

*단위 %*

![공개된 개선 폭](<contents/figures/s12-01.png>)

| 주체 | 내용 | 수치 | 출처 |
|---|---|---|---|
| 삼성전자 | 설계 특화 Agent 적용, HBM4 개발 리드타임 | 50% 단축 | 머니투데이 2026.3 (Synopsys 공동 발표) |
| Micron | AI 도입 후 목표 불량률(DPM) 도달 속도 | 35% 단축 | EE Times Asia 2017 |
| Micron | AI 도입 후 목표 수율 도달 속도 | 25% 단축 | EE Times Asia 2017 |
| McKinsey 사례 | 수율 전담 조직 운영 6개월, 수율 개선 / 비용 절감 | 10% / $1,200만 | McKinsey 2018 |
| 미국 에너지부 | 예측 정비 도입 시 운영비 절감 / 생산량 증가 | 30~40% / 20~25% | DOE 보고서 (SemiEngineering 인용) |

---

<a id="s13"></a>

## 13. 대안 비교 및 선정 근거

### 13.1 대안 비교

| 평가 기준 | 수작업 유지 | 분석 솔루션 기능 확장 | 사내 범용 챗봇 | TRACE |
|---|---|---|---|---|
| 조사 과정 자동화 | 없음 | 분석 화면 중심 | 질의응답 수준 | **접수·5단계 조사~보고서 전 과정** |
| 수치 정합성 | 담당자 의존 | 높음 | LLM 생성 위험 | **Python 도구 계산, 재현 가능** |
| 근거 추적 | 낮음 | 데이터만 | 문서만 | **데이터 + SOP 조항 원문** |
| 근거 없는 결론 차단 | 담당자 의존 | 해당 없음 | 없음, 환각 위험 | **출처 없는 주장 배제·사례 없으면 종료** |
| 이기종 시스템 연동 | - | 자사 플랫폼 종속 | 문서 저장소만 | **MCP 이중 도구 체계** |
| 승인·감사 통제 | 수기 | 제한적 | 없음 | **HITL Interrupt + 승인 스냅샷** |
| 도입 부담 | 없음 | 라이선스·플랫폼 전환 | 낮음 | **기존 시스템 유지** |

### 13.2 선정 근거

1. **비어 있는 구간에 직접 대응.** 기존 FDC 투자를 바꾸지 않고 감지 직후의 조사·비교·매뉴얼 확인·기록·인계만 자동화합니다.
2. **현장이 믿을 수 있는 구조.** 수치는 코드로, 근거는 조항 원문으로, 결론은 가설과 엔지니어 승인으로 다룹니다.
3. **장비사에 묶이지 않는 연동.** 데이터 연결을 `businessmcp`·`ragmcp` 도구 단위로 나눠 장비·시스템이 달라도 교체해 연결합니다.
4. **업무 규칙의 단일 관리.** 조사 상태·승인 규칙과 저장은 Backend에 두고, Business MCP도 내부 API를 거쳐 같은 권한·감사 정책을 적용합니다.
5. **다른 공정으로 확장.** 같은 흐름을 습식 식각과 증착·CMP 공정, 디스플레이·이차전지 장비에 재사용합니다.

---

<a id="s14"></a>

## 14. 산업 동향

### 14.1 주요 발표

| 시점 | 주체 | 내용 |
|---|---|---|
| 2025.01 | Cohu | AI 공정 제어·이상 감지 기업 Tignis 인수 완료 |
| 2026.03 | 삼성전자 | 설계~제조 전 과정에 에이전틱 AI 적용, 2030년 AI 자율공장 전환 목표 |
| 2026.06 | 산업통상부 | 2030년까지 제조 AI 민관 20조 원 투입, 제조 AI 도입률 40% 목표 |
| 2026.08 | PDF Solutions | Exensio Aurora 공개, 에이전트형 "가상 선임 엔지니어" 지향 |
| 2026.09 | SK하이닉스 | 라인 이상 시 AI가 원인·대응 방안을 제시하고 사람이 최종 판단하는 체계로 전환 계획, 반도체 특화 생성형 AI 플랫폼 GaiA 운영 |
| 2026.09 | 세미에이아이 | 공정·장비·계측·결함 전문 Agent 기반 수율 원인 추적 플랫폼 SMILE 발표 |

*TRACE의 문제 정의와 승인 구조는 SK하이닉스가 밝힌 전환 방향과 일치합니다.*

### 14.2 관련 시장 규모

#### Lam Research 매출 구성 (FY2025)

*단위 USD 억 · 식각 장비 1위 업체*

![Lam Research 매출 구성 (FY2025)](<contents/figures/s14-01.png>)

<sub>Counterpoint Research</sub>

#### FDC 소프트웨어 시장

*단위 USD 억 · 연평균 8.7% 성장 전망*

![FDC 소프트웨어 시장](<contents/figures/s14-02.png>)

<sub>Global Market Insights</sub>

*이미 설치된 장비를 관리하는 사업만 연 $70억 규모로, 설치 장비 운영 효율화 수요가 크다는 점을 보여 줍니다.*

---

<a id="s15"></a>

## 15. 도입 로드맵과 확장 계획

### 15.1 도입 로드맵

![도입 4단계](<contents/figures/s15-01.png>)

| 단계 | 주요 산출물 | 완료 기준 |
|---|---|---|
| Phase 0. PoC | 5장 아키텍처 전체(Vue · Nginx · FastAPI · LangGraph · MCP · Keycloak · PostgreSQL), 건식 이온밀 기반 샘플 사례, SOP 3종·OCAP 19종 색인, 평가 질문 세트 | 16장 시연 항목 전부 수행, 수치 정합성 100%, 승인 전 저장 0건 |
| Phase 1. Pilot | 건식 식각 진공·압력, 가스, 냉각 3계통 우선 적용. 고객사 센서 Trace·MES Run/Step·정비 이력을 `businessmcp` 어댑터로 연동, 사내 문서 색인 | 기준선 대비 MTTI·공수 개선 확인 |
| Phase 2. 건식·습식 확장 | 습식 식각 데이터 어댑터와 SOP/OCAP 색인 추가, 라인 내 식각 장비 전체 적용, 사내 계정 체계와 역할 기반 권한(작업자·엔지니어·관리자)·담당 배정 연동, 승인 이력 재사용 검색 | 건식·습식 평가 세트 통과, Lot Hold 시간 개선 |
| Phase 3. 고도화 | 센서 시계열 ML/DL 모델을 MCP Tool로 연결, 공정별 Tool 확장, 대기열 기반 비동기 처리와 다중 사이트 운영 | 시계열 모델 오프라인 평가 통과, 운영 SLA 충족 |

### 15.2 서비스 확장 계획

지금까지는 식각 공정 중 **건식 식각의 이온밀(Ion Mill) 데이터**를 위주로 조사 흐름을 검증했습니다. 이를 확장해 **건식·습식 식각을 모두 커버하는 서비스**로 넓힐 예정이며, 가능하면 Run 단위 요약값 비교를 넘어 **시계열 데이터 자체를 트래킹하는 ML/DL 모델**로의 확장도 고려하고 있습니다.

![데이터 범위와 분석 방식의 확장 방향](<contents/figures/s15-02.png>)

| 확장 축 | 현재 | 확장 방향 | TRACE 변경 |
|---|---|---|---|
| 건식·습식 식각 | 건식 식각 중 이온밀 장비의 센서·고장 데이터 위주 | 플라즈마 건식(RIE·ICP)과 습식 식각까지 커버. 습식은 약액 농도·온도·순환 유량·Bath 수명·린스·건조 등 다른 변수와 이상 유형을 다룸 | 조사 조건에 공정 유형(건식·습식) 추가, `businessmcp` 데이터 어댑터와 SOP/OCAP 색인을 공정별로 추가, Sensor·Maintenance Agent의 분석 관점을 공정별로 분기. Graph 구조는 그대로 유지 |
| 시계열 ML/DL | Run 단위 요약값의 평균·편차·z-score 비교 | 센서 시계열 자체를 추적하는 ML/DL 모델 검토: 이상 구간 탐지(오토인코더·LSTM 계열), 변화점 탐지, 고장까지 남은 시간 예측 | 모델을 별도 서빙하고 MCP Tool로 노출해 Sensor Agent가 호출. 모델 결과도 모델 버전·입력 구간을 출처로 붙여 근거로 사용하고, 최종 판단은 엔지니어 승인 유지 |

---

<a id="s16"></a>

## 16. 최종 시연 계획

로그인한 사용자로 질문부터 승인·확정 저장까지 한 흐름으로 보여 주고, 오류 복구와 Trace를 이어서 확인합니다.

| 순서 | 장면 | 보여 줄 내용 | 평가 항목 |
|---|---|---|---|
| 1 | 아이템·구성도 소개 | Pain Point와 5.1 구성도, 서비스 책임과 네트워크 경계 | 아이템, 아키텍처 |
| 2 | 로그인 게이트 | Keycloak PKCE 로그인, 로그인 전 화면 접근 차단 | 인증 |
| 3 | 이상 접수 | 질문 전송 → `202 taskId` → SSE 진행 타임라인 | 화면·API |
| 4 | 재질문과 재개 | 누락 필드 재질문, 답변 후 같은 작업 재개 | Agent 설계·구현 |
| 5 | State·Graph | 6.2 실행 흐름과 현재 Node, State의 사례·비교 결과·budget 값 | Agent 설계 |
| 6 | Tool 선택과 조회 | 범위 조사·Run 비교 Agent의 `businessmcp` 호출, 추천 Agent의 `ragmcp` 검색 이벤트 | MCP, Agent 구현 |
| 7 | 출처 포함 보고서 | 근거 칩과 원문 Resource 열기 | MCP, 화면 |
| 8 | 승인 전 멈춤 | 검토 화면에서 변경 Tool·인자 확인, 승인 전 저장 없음 | Harness |
| 9 | 승인 후 재개 | 승인 → 같은 thread 재개 → `save_investigation` → DONE | Agent 구현 |
| 10 | 도구 오류와 복구 | MCP 타임아웃 주입 → 재시도 → 복구 또는 FAILED 사유, 같은 thread로 재실행 | Harness |
| 11 | Trace | Trace ID 기준 Node·Tool·지연·Token·비용 | Harness |
| 12 | 인증 실패 | 토큰 없음·만료 토큰 요청 → 401, 승인 이력에 승인자 기록 확인 | 인증 |

<sub>제출 자료: 서비스 아이템 설명, 5.1 구성도와 5.4·5.6 순서도, 6.2 실행 흐름, 7장 Tool 명세, 9.2 평가 결과, 시연 영상</sub>

---

<a id="s17"></a>

## 17. 리스크 및 대응

| 리스크 | 내용 | 대응 |
|---|---|---|
| 데이터 보안 | 공정 데이터는 외부 반출 불가 | 사내망 설치형, 외부 모델에는 계산된 요약값만 전송, 사내 LLM·임베딩 연결 옵션 |
| 데이터 형식 차이 | 장비사·시스템마다 형식과 식별자가 다름 | MCP 도구 단위 어댑터, 데이터 사전 기반 매핑 |
| 권한 구분 부재 | 로그인 사용자가 같은 권한이라 승인 책임 범위가 넓음 | 모든 승인에 승인자·시각 기록, 역할 기반 권한과 담당 배정은 확장 단계에서 추가 (15장) |
| 외부 LLM 의존 | API Key가 없거나 외부 모델 장애 | 제한 모드로 동작, 사내 LLM·임베딩 연결 옵션 |
| 문서 조건 오적용 | Pumpdown·Main Etch처럼 같은 키워드라도 적용 조항이 다름 | 장비·Step 메타 필터, 평가 질문 세트에 문맥 구분 사례 포함 |
| AI 오류 | 근거 없는 원인 추정, 숫자 오기, 미검증 조치의 해결 단정 | 숫자 생성 금지, 출처 필수, 가설 분리, 유사 사례가 없으면 종료, 승인 통제 |
| 응답 지연·비용 | 모델 호출 증가로 대기 시간과 비용 상승 | 8턴·120초 한도, 202 접수와 SSE, Trace 기반 Token·비용 모니터링 |
| 현장 수용성 | 엔지니어가 AI 결과를 믿지 않음 | 계산 근거·조항 원문 공개, 수정 요청 반영, 최종 판단은 엔지니어 유지 |
| PoC 데이터 한계 | PHM 공개 데이터는 건식 식각 중 이온밀 장비로, 양산 플라즈마 식각·습식 식각과 다름 | PoC는 조사 절차 검증으로 한정, 건식·습식 확장(15.2)과 Pilot에서 효과 측정 |

---

<a id="s18"></a>

## 18. 결론 및 요청 사항

### 18.1 결론

식각 공정은 점점 어려워지고 장비는 늘어나는데, 이상 감지 이후의 조사·비교·매뉴얼 확인·기록·인계는 아직 엔지니어 손에 남아 있습니다. TRACE는 기존 시스템을 그대로 둔 채 이 구간을 접수·5단계 전문 조사·보고·승인의 Agent 흐름으로 자동화하고, Python 계산·조항 원문 근거·엔지니어 승인으로 현장에서 믿고 쓸 수 있는 조사 기록을 만듭니다. 건식 이온밀 데이터로 검증한 흐름을 건식·습식 식각 전체와 시계열 ML/DL 분석으로 넓혀, 승인된 기록이 다음 조사의 근거로 쌓이는 구조를 만듭니다.

### 18.2 Pilot 요청 사항

1. Pilot 대상 식각 장비군 1종(진공·압력, 가스, 냉각 계통 우선)과 최근 이상 조사 사례 10건 내외 제공
2. 센서 Trace, MES Run/Step, 레시피, 정비(PM) 이력, SOP·OCAP 문서 접근 범위 협의
3. 평가 질문의 정답 판정과 조사 시간·공수 기준선 측정을 함께할 현업 담당자 지정

---

<a id="s19"></a>

## 19. 출처

- [Lam Research – 2025 Investor Day](https://filecache.investorroom.com/mr5ir_lamresearch2/1435/Lam%20Research%202025%20Investor%20Day%20FINAL.pdf)
- [arXiv 2507.10564 – Tool-to-Tool Matching Analysis (Samsung)](https://arxiv.org/html/2507.10564v1)
- [Silicon Semiconductor – Quick to find fault](https://siliconsemiconductor.net/article/68003/Quick_to_find_fault/feature)
- [WSTS – Global Semiconductor Market Q2 2026](https://www.wsts.org/76/Global-Semiconductor-Market-records-exceptional-growth-in-Q2-2026)
- [SEMI – Equipment Billings Reached $135 Billion in 2025](https://www.semi.org/en/SEMI-Reports-Global-Semiconductor-Equipment-Billings-Reached-135-Billion-in-2025)
- [SEMI – Equipment Sales Forecast $229 Billion in 2028](https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-forecast-to-reach-a-record-229-billion-dollars-in-2028-semi-reports)
- [SemiconductorX – Front-End Fabrication](https://semiconductorx.com/front-end-fabrication-overview.html)
- [SemiconductorX – Etch](https://semiconductorx.com/wfe-etching.php)
- [SemiconductorX – 3D NAND](https://semiconductorx.com/fabs-3d-nand.php)
- [뉴데일리 – 반도체 인력 부족 전망](https://biz.newdaily.co.kr/site/data/html/2024/06/24/2024062400063.html)
- [SemiEngineering – Getting Smarter About Tool Maintenance](https://semiengineering.com/getting-smarter-about-tool-maintenance/)
- [Guru3D – TSMC 2nm Wafer Cost](https://www.guru3d.com/story/tsmc-2nm-wafer-cost-explained-price-breakdown)
- [McKinsey – Semiconductor Yield Improvement](https://www.mckinsey.com/~/media/McKinsey/Industries/Semiconductors/Our%20Insights/Taking%20the%20next%20leap%20forward%20in%20semiconductor%20yield%20improvement/Taking-the-next-leap-forward-in-semiconductor-SHORT.pdf)
- [EE Times Asia – AI Reshaping Fab Operations](https://www.eetasia.com/ai_fab_operations/)
- [Counterpoint – Lam Research FY2025](https://counterpointresearch.com/cn/insights/lam-research-posts-record-fy-2025-revenue-driven-by-strong-systems-sales-1)
- [Global Market Insights – FDC Market](https://www.gminsights.com/industry-analysis/fault-detection-and-classification-market/market-size)
- [Business Wire – Cohu to Acquire Tignis](https://www.businesswire.com/news/home/20241216636156/en)
- [머니투데이 – 삼성전자 반도체 공정 AI](https://www.mt.co.kr/world/2026/03/18/2026031808352363202)
- [머니투데이 – 제조AI 20조 투입](https://www.mt.co.kr/article/2026062914212298001)
- [한국경제 – SK하이닉스 2026 미래포럼](https://www.hankyung.com/article/202609094433i)
- [SemiWiki – PDF Solutions Exensio Aurora](https://semiwiki.com/artificial-intelligence/372347-pdf-solutions-exensio-was-built-for-semiconductor-analytics-the-new-exensio-aurora-architecture-is-built-for-semiconductor-intelligence/)
- [벤처스퀘어 – 세미에이아이](https://www.venturesquare.net/1107509/)
- [PHM Society – 2018 Data Challenge](https://phmsociety.org/wp-content/uploads/2018/05/PHM-Data-Challenge-2018-vFinal-v2_0.pdf)
