// Mock-only sample data. Shapes follow docs/frontend.md (필요 API) and docs/api.md.
import type { Report, Sop } from '../src/api/types'

// Sample SOPs moved from the former hard-coded src/api/sop.ts.
export const sopDocuments: Omit<Sop, 'demo'>[] = [
  {
    id:'OCAP-ETCH-PRS', title:'챔버 압력 이상 대응', category:'OCAP', version:'1.1', updatedAt:'2026-10-20', owner:'Etch설비기술팀',
    description:'챔버 압력 이상 대응 시 1차 확인 항목(목업 요약). 실제 원문은 sop-ocap/ 문서입니다.', tags:['OCAP'],
    markdown:`> **목업 요약**: 실제 원문은 저장소 \`sop-ocap/OCAP-ETCH-PRS_*.md\`이며 backend \`/api/sops\`가 제공합니다.

## 4.4 확인 데이터
pressure error, valve command·position, pump speed·current, foreline pressure, gas flow

## 비교 방법
같은 chamber·recipe·step의 이전 Run과 비교합니다. 현재 목업에는 승인 관리한계가 없습니다.`,
  },
  {
    id:'OCAP-ETCH-RF', title:'RF 반사전력 이상 대응', category:'OCAP', version:'1.1', updatedAt:'2026-10-20', owner:'Etch설비기술팀',
    description:'RF 반사전력 이상 대응 시 1차 확인 항목(목업 요약). 실제 원문은 sop-ocap/ 문서입니다.', tags:['OCAP'],
    markdown:`> **목업 요약**: 실제 원문은 저장소 \`sop-ocap/OCAP-ETCH-RF_*.md\`이며 backend \`/api/sops\`가 제공합니다.

## 4.4 확인 데이터
forward·reflected power, matching tuning 위치, RF 케이블·커넥터 상태

## 비교 방법
같은 chamber·recipe·step의 이전 Run과 비교합니다. 현재 목업에는 승인 관리한계가 없습니다.`,
  },
  {
    id:'OCAP-ETCH-GAS', title:'가스 유량 이상 대응', category:'OCAP', version:'1.1', updatedAt:'2026-10-20', owner:'Etch설비기술팀',
    description:'가스 유량 이상 대응 시 1차 확인 항목(목업 요약). 실제 원문은 sop-ocap/ 문서입니다.', tags:['OCAP'],
    markdown:`> **목업 요약**: 실제 원문은 저장소 \`sop-ocap/OCAP-ETCH-GAS_*.md\`이며 backend \`/api/sops\`가 제공합니다.

## 4.4 확인 데이터
MFC setpoint·readback, 가스 라인 압력, 밸브 상태

## 비교 방법
같은 chamber·recipe·step의 이전 Run과 비교합니다. 현재 목업에는 승인 관리한계가 없습니다.`,
  },
  {
    id:'OCAP-ETCH-TMP', title:'온도·후면 냉각 이상 대응', category:'OCAP', version:'1.1', updatedAt:'2026-10-20', owner:'Etch설비기술팀',
    description:'온도·후면 냉각 이상 대응 시 1차 확인 항목(목업 요약). 실제 원문은 sop-ocap/ 문서입니다.', tags:['OCAP'],
    markdown:`> **목업 요약**: 실제 원문은 저장소 \`sop-ocap/OCAP-ETCH-TMP_*.md\`이며 backend \`/api/sops\`가 제공합니다.

## 4.4 확인 데이터
ESC 온도, 후면 He 압력·유량, 칠러 온도·유량

## 비교 방법
같은 chamber·recipe·step의 이전 Run과 비교합니다. 현재 목업에는 승인 관리한계가 없습니다.`,
  },
  {
    id:'SOP-ETCH-12', title:'식각 공정 이상 대응 절차', category:'공정 이상 대응',
    version:'1.2', updatedAt:'2026-10-12', owner:'공정기술팀',
    description:'이상 접수부터 근거 확인, 점검 계획과 검토 기록까지의 흐름입니다.',
    tags:['식각', 'Endpoint', '이상 조사'],
    markdown:`> **샘플 문서**: 화면 시연을 위한 예시입니다. 실제 작업에는 승인된 현장 지침을 사용하세요.

## 1. 목적
식각 이상이 관찰됐을 때 조사에 필요한 정보를 누락 없이 기록합니다.

## 2. 접수 정보
| 항목 | 기록 내용 |
| --- | --- |
| 조사 범위 | 장비, 챔버 또는 레시피 |
| 관찰 현상 | Endpoint 지연, Etch rate 저하 등 |
| 계측값 | 측정 시점, 값, 단위, 원본 출처 |

## 3. 조사 순서
1. 현재 관찰된 사실과 측정 조건을 확인합니다.
2. 같은 조건의 과거 사례와 수치 근거를 비교합니다.
3. 관련 문서 조항과 연결해 확인할 가설을 정리합니다.
4. 엔지니어의 검토 의견과 결정을 기록합니다.

## 4. 기록 원칙
- 원인 가설과 확인된 사실을 구분합니다.
- 수치에는 단위와 근거 사례 ID를 남깁니다.
- 점검이나 조건 변경은 현장 승인 절차를 따릅니다.
`
  },
  {
    id:'SOP-RF-03', title:'RF 반사전력 이상 조사 가이드', category:'장비 점검',
    version:'1.0', updatedAt:'2026-10-08', owner:'설비기술팀',
    description:'RF 반사전력 상승 시 확인할 이력과 조사 기록의 예시입니다.',
    tags:['RF', '반사전력', '장비'],
    markdown:`> **샘플 문서**: 실제 장비 조작이나 정비를 위한 지침이 아닙니다.

## 적용 범위
RF 반사전력 상승이 관찰된 식각 공정의 이력을 검토합니다.

## 사전 확인
- 장비·챔버·레시피와 발생 시점을 확인합니다.
- 최근 정비·교정 이력이 있는지 확인합니다.
- 측정 단위와 비교 대상의 조건이 같은지 확인합니다.

## 확인할 근거
| 구분 | 확인 내용 |
| --- | --- |
| 계측 이력 | 반사전력 변화와 동시 발생한 공정 변화 |
| 과거 사례 | 유사 조건의 점검 결과와 적용 가능성 |
| 정비 이력 | 작업 전후 관찰값과 승인 기록 |

## 검토 기록 예시
\`\`\`text
관찰 사실: 측정값과 시점을 기록
확인 가설: 아직 검증하지 않은 가능성을 구분
다음 확인: 담당자가 검토할 근거와 항목을 기록
\`\`\`

**주의:** 과거 사례에서 확인된 원인을 현재 장비의 원인으로 단정하지 않습니다.
`
  },
  {
    id:'SOP-PM-07', title:'챔버 점검 전후 기록 절차', category:'예방 정비',
    version:'2.0', updatedAt:'2026-09-25', owner:'설비기술팀',
    description:'챔버 점검의 전후 비교와 승인 이력 작성 예시입니다.',
    tags:['챔버', '예방 정비', '기록'],
    markdown:`> **샘플 문서**: 작업 안전·정비 순서는 승인된 별도 절차를 따릅니다.

## 1. 점검 전
1. 대상 장비와 챔버를 식별합니다.
2. 관찰된 현상과 기준 자료를 보존합니다.
3. 관련 조사 기록과 정비 이력을 확인합니다.

## 2. 점검 후 기록
- 수행한 작업의 승인된 기록을 연결합니다.
- 전후 비교값의 조건·단위·출처를 남깁니다.
- 확인되지 않은 결과는 확인되지 않은 상태로 기록합니다.

## 3. 검토 및 보존
| 기록 | 보존할 정보 |
| --- | --- |
| 검토 의견 | 검토자의 판단과 추가 확인 요청 |
| 승인 | 승인자, 승인 시각, 보고서 버전 |
| 후속 확인 | 확인 결과와 원본 조사 링크 |

---

기록 수정 시에는 **원래 근거를 추적할 수 있도록** 변경 이력을 보존합니다.
`
  }
];

const documents = {
  'DOC-RF-03': {id:'DOC-RF-03', title:'RF 반사전력 점검 기준', text:'반사전력이 기준 대비 지속 상승하면 매칭 네트워크와 RF 케이블 체결 상태를 우선 확인한다. (샘플 문서)'},
  'DOC-EP-07': {id:'DOC-EP-07', title:'Endpoint 지연 대응', text:'Endpoint가 레시피 기준보다 20% 이상 늦어지면 챔버 컨디셔닝 이력과 OES 신호를 비교한다. (샘플 문서)'},
  'DOC-PR-02': {id:'DOC-PR-02', title:'챔버 압력 안정화 확인', text:'압력 변동이 관찰되면 스로틀 밸브 응답과 가스 유량 로그를 함께 확인한다. (샘플 문서)'},
}

// SOP RAG clauses as `search_sop` returns them: id `<문서ID>#<절>`, title `<문서> · <절 제목>`.
const sopClauses = [
  {id:'SOP-ETCH-12#4.2', title:'SOP-ETCH-12 식각 장비 이상 대응 · 4 절차 / 4.2 Endpoint 지연 시 동시 비교',
    text:'Endpoint 지연이 관찰되면 같은 Recipe·Step의 직전 정상 run과 OES 신호, 반사전력, 챔버 압력을 동시에 비교한다. (목업 조항)'},
  {id:'SPEC-RF-03#2.1', title:'SPEC-RF-03 RF 계통 판정 기준 · 2 판정 기준 / 2.1 반사전력',
    text:'반사전력이 기준 대비 지속 상승하면 매칭 네트워크 위치와 RF 케이블 체결 상태를 우선 확인한다. (목업 조항)'},
  {id:'SOP-ETCH-12#4.4', title:'SOP-ETCH-12 식각 장비 이상 대응 · 4 절차 / 4.4 계통별 1차 점검 분기',
    text:'RF, 가스, 배기, 챔버 상태 순으로 1차 점검 분기를 정하고 확인 결과를 기록한다. (목업 조항)'},
].map(item => ({...item, is_demo:true, source:'sop/mock.md', revision:'Rev.3', notice:'목업 문서 조항입니다.', distance:0.21}))

// Builds a report for the mock agent. `feedback` holds the engineer's revision requests.
export function buildReport(question: string, feedback: string[]): Report {
  const equipment = question.match(/ETCH-\d+/)?.[0] ?? 'ETCH-07'
  const chamber = question.match(/CH-[A-Z]/)?.[0] ?? 'CH-B'
  const recipe = question.match(/OX-\d+/)?.[0] ?? 'OX-120'
  const rfFocus = feedback.some(item => /RF/i.test(item))
  return {
    context:{equipment, chamber, recipe, symptom:question},
    metrics:[
      {key:'endpoint_sec', value:118, severity:'high', mean:92.4, deltaPct:27.7, z:3.1},
      {key:'rf_reflected_w', value:29, severity:rfFocus ? 'high' : 'medium', mean:18.2, deltaPct:59.3, z:2.4},
      {key:'pressure_mtorr', value:31.5, severity:'low', mean:30.1, deltaPct:4.7, z:0.8},
    ],
    physicsResults:[
      {model:'etch_depth_constant_rate', version:'1.0', status:'needs_more_data', formula:'D = R * t', inputs:[], result:null,
        assumptions:['식각 시간 동안 평균 식각 속도가 일정합니다.'], missing_fields:['etch_rate_nm_min', 'etch_time_sec'], warnings:[]},
      {model:'average_etch_rate', version:'1.0', status:'needs_more_data', formula:'R = (D0 - D1) / t', inputs:[], result:null,
        assumptions:['전후 막 두께 차이가 제거 두께를 나타냅니다.'], missing_fields:['pre_thickness_nm', 'post_thickness_nm', 'etch_time_sec'], warnings:[]},
      {model:'selectivity', version:'1.0', status:'needs_more_data', formula:'S = R_target / R_mask', inputs:[], result:null,
        assumptions:['두 속도는 동일 조건에서 측정되었습니다.'], missing_fields:['target_etch_rate_nm_min', 'mask_etch_rate_nm_min'], warnings:[]},
    ],
    causeCases:[
      {id:'CASE-014', cause:'RF matching 열화', action:'매칭 네트워크 커패시터 위치와 반사전력 추이 확인', docs:['DOC-RF-03']},
      {id:'CASE-031', cause:'챔버 컨디셔닝 부족', action:'최근 PM 이후 시즈닝 웨이퍼 수 확인', docs:['DOC-EP-07']},
      ...(rfFocus ? [{id:'CASE-042', cause:'RF 케이블 체결 불량', action:'케이블 토크와 커넥터 손상 여부 확인', docs:['DOC-RF-03']}] : []),
    ],
    docIds:['DOC-RF-03', 'DOC-EP-07', 'DOC-PR-02'],
    documents:[...Object.values(documents), ...sopClauses],
    // Six specialist-agent results in graph order.
    stages:[
      {key:'scope', title:'범위 조사 에이전트', status:'sample_based', agent_mode:'rule_based',
        findings:[`${equipment} ${chamber} ${recipe} 범위에서 유사 데모 사례 3건과 승인 이력 1건을 찾았습니다.`],
        unknowns:['MES Lot/Wafer와 실제 Run 목록 미연결'], caseIds:['CASE-014', 'CASE-031'], historyIds:['HIST-1020'], docIds:[]},
      {key:'run_comparison', title:'동일 조건 Run 비교 에이전트', status:'sample_based', agent_mode:'rule_based',
        findings:['endpoint가 비교군 평균 대비 27.7% 지연, RF 반사전력 59.3% 상승'],
        unknowns:['동일 Recipe·Step 실측 Run 시계열 미연결'], caseIds:['CASE-014'], docIds:[]},
      {key:'physics', title:'물리 관계식 검증 에이전트', status:'unavailable', agent_mode:'rule_based',
        findings:[], unknowns:['식각 시간·막 두께·선택비 입력 데이터가 필요합니다.'], caseIds:[], docIds:[]},
      {key:'sensor', title:'센서 교차 확인 에이전트', status:'partial', agent_mode:'rule_based',
        findings:['사용자 입력 계측값(endpoint, RF reflected)만 확인했습니다.'],
        unknowns:['Gas Flow·펌프·밸브 원본 센서 시계열 미연결'], caseIds:[], docIds:[]},
      {key:'maintenance', title:'정비 이력 확인 에이전트', status:'unavailable', agent_mode:'rule_based',
        findings:[], unknowns:['정비 API/MCP 미연결로 정비 이력을 조회하지 않았습니다.'], caseIds:[], docIds:[]},
      {key:'recommendation', title:'원인 후보·점검 순서 추천 에이전트', status:'provisional', agent_mode:'rule_based',
        findings:['RF 매칭 계통을 먼저 확인하고 챔버 컨디셔닝 이력을 이어서 확인할 것을 권고합니다.'],
        unknowns:['원인 확정이 아니며 현장 데이터 검증이 필요합니다.'], caseIds:['CASE-014', 'CASE-031'], docIds:sopClauses.map(item => item.id)},
    ],
    // RAG MCP clauses, in reranked order (develop `checks`).
    checks:sopClauses.map(item => ({title:item.title, rationale:item.text, source:'rag_mcp' as const, docId:item.id})),
    // Similar approved records visible to the requester (develop `history`).
    history:[{id:'HIST-1020', question:'ETCH-07 CH-B endpoint 112초 지연', summary:'RF 매칭 네트워크 커패시터 위치 이상으로 확인 가설 승인',
      causes:['RF matching 열화'], docIds:['DOC-RF-03'], approvedBy:'이엔지니어', approvedAt:'2026-10-12 14:20', eventTime:'2026-10-12 13:05', lotId:'LOT-261012-07'}],
    summary:`${equipment} ${chamber} ${recipe}에서 endpoint가 비교군 평균 대비 27.7% 지연되고 RF 반사전력이 59.3% 높습니다. ` +
      `유사 사례 ${rfFocus ? 3 : 2}건 기준으로 RF 매칭 계통을 먼저 확인할 가설을 제시합니다.` +
      (feedback.length ? ` 수정 요청 반영: ${feedback.join(' / ')}` : ''),
    unknowns:['정비 이력 원본 미확인'],
    feedback,
    demo:true,
  }
}
