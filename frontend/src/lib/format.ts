export const labels: Record<string, string> = {endpoint_sec:'Endpoint', etch_rate_nm_min:'Etch rate', rf_reflected_w:'RF reflected', pressure_mtorr:'Pressure'}
export const units: Record<string, string> = {endpoint_sec:'sec', etch_rate_nm_min:'nm/min', rf_reflected_w:'W', pressure_mtorr:'mTorr'}
export const statuses: Record<string, string> = {
  QUEUED:'접수됨', RUNNING:'조사 중', SEARCH_STARTED:'근거 검색 중',
  ANALYSIS_STARTED:'수치 분석 중', REPORT_STARTED:'보고서 작성 중',
  WAITING_INPUT:'추가 정보 대기', WAITING_APPROVAL:'엔지니어 판별 대기',
  DONE:'완료', INCOMPLETE:'근거 부족', FAILED:'실패', REVIEWED:'판별됨', LOADING:'조사 불러오는 중'
}
export const terminal = new Set(['DONE', 'INCOMPLETE', 'FAILED'])

// UUIDs are unreadable in lists; show the first block and keep the full id in a tooltip.
export const shortId = (id: string) => /^[0-9a-f]{8}-/i.test(id) ? id.slice(0, 8) : id

// Readable record history line for a saved event; detail is the human text, if any.
export function eventLine(event: {type: string, payload?: Record<string, any>}): {title: string, detail?: string} {
  const payload = event.payload || {}
  switch (event.type) {
    case 'QUEUED': return {title:'조사 접수'}
    case 'RUNNING': return {title:'에이전트 실행'}
    case 'SEARCH_STARTED': return {title:'근거 검색'}
    case 'ANALYSIS_STARTED': return {title:'근거 분석'}
    case 'REPORT_STARTED': return {title:'보고서 작성'}
    case 'MESSAGE': return {title:'엔지니어 답변', detail:text(payload.text)}
    case 'QUESTION': return {title:'에이전트 재질문', detail:text(payload.text)}
    case 'APPROVAL_REQUIRED': return {title:'보고서 판별 요청'}
    case 'REVIEWED': return {title:payload.action === 'approve' ? '승인' : '미승인', detail:payload.comment ? text(payload.comment) : undefined}
    case 'DONE': return {title:'조사 완료'}
    case 'FAILED': return {title:'실패', detail:text(payload.error)}
    case 'INCOMPLETE': return {title:'근거 부족으로 종료', detail:text(payload.reason)}
    default: return {title:event.type}
  }
}

export const stageStatus: Record<string, string> = {
  sample_based:'데모 사례 기반', partial:'일부 확인 · 연관 데이터 미연결',
  unavailable:'데이터 미연결', provisional:'임시 권고'
}
export const agentMode = (mode?: string) => mode === 'llm' ? 'LLM 사용' : '규칙 기반 실행'
// Compact labels for the narrow sidebar; the report keeps the full wording.
const stageShort: Record<string, string> = {sample_based:'데모 사례', partial:'일부 확인', unavailable:'데이터 미연결', provisional:'임시 권고'}

// Agent graph: intake, six specialist agents, report, review.
export const AGENT_FLOW = [
  {key:'intake', title:'질문 접수', hint:'범위·이상 현상 확인'},
  {key:'scope', title:'범위 조사', hint:'유사 사례·승인 이력'},
  {key:'run_comparison', title:'과거 Run 비교', hint:'계측값 통계 비교'},
  {key:'physics', title:'물리 관계식 검증', hint:'계산값·부족 데이터'},
  {key:'sensor', title:'센서 교차 확인', hint:'연관 센서 구분'},
  {key:'maintenance', title:'정비 이력 확인', hint:'정비·변경 이력'},
  {key:'recommendation', title:'원인 후보·점검 추천', hint:'SOP RAG 검색'},
  {key:'report', title:'보고서 구성', hint:'근거 연결'},
  {key:'review', title:'엔지니어 판별', hint:'승인·미승인'},
] as const

export type FlowState = 'done' | 'active' | 'stopped' | 'pending'
export interface FlowStep { key: string, title: string, hint: string, state: FlowState, result?: string }

// Progress comes only from saved events. Sensor, maintenance and recommendation emit
// no events of their own, so ANALYSIS_STARTED marks the whole specialist run active.
// Each agent's outcome is read from report.stages once the report exists.
export function agentFlow(events: {type: string, payload?: Record<string, any>}[],
                          report?: {stages?: {key: string, status: string, agent_mode?: string}[]} | null): FlowStep[] {
  let active: number[] = [0]
  let finished = false
  let stopped = false
  let reviewed = false
  for (const event of events) {
    if (event.type === 'SEARCH_STARTED') active = [1]
    else if (event.type === 'ANALYSIS_STARTED') active = [2, 3, 4, 5, 6]
    else if (event.type === 'REPORT_STARTED') active = [7]
    else if (event.type === 'APPROVAL_REQUIRED') { active = [8]; reviewed = true }
    else if (event.type === 'REVIEWED') active = event.payload?.action === 'approve' ? [8] : [7]
    else if (event.type === 'QUESTION') active = reviewed ? [8] : [0]
    else if (event.type === 'DONE') finished = true
    else if (event.type === 'FAILED' || event.type === 'INCOMPLETE') stopped = true
  }
  const first = Math.min(...active)
  const stages = new Map((report?.stages || []).map(stage => [stage.key, stage]))
  return AGENT_FLOW.map((step, index) => {
    const stage = stages.get(step.key)
    const state: FlowState = finished ? 'done' : active.includes(index) ? (stopped ? 'stopped' : 'active') :
      index < first ? 'done' : 'pending'
    return {...step, state, result:stage ? `${stageShort[stage.status] || stage.status} · ${stage.agent_mode === 'llm' ? 'LLM' : '규칙'}` : undefined}
  })
}

export function text(value: unknown): string {
  return typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value, null, 2)
}
export function date(value: unknown): string {
  if (!value) return '미제공'
  const parsed = new Date(value as string)
  return Number.isNaN(parsed.getTime()) ? String(value) :
    new Intl.DateTimeFormat('ko-KR', {dateStyle:'medium', timeStyle:'short'}).format(parsed)
}
export const number = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '미제공'
