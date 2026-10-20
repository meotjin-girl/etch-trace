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

// Sidebar progress (1-4) derived only from backend events and the report.
export function progressStep(events: {type: string}[], hasReport: boolean): number {
  let value = 1
  for (const event of events) {
    if (event.type === 'SEARCH_STARTED') value = 2
    if (event.type === 'ANALYSIS_STARTED') value = 3
    if (['REPORT_STARTED', 'APPROVAL_REQUIRED', 'DONE'].includes(event.type)) value = 4
  }
  return hasReport ? 4 : value
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
