export const labels: Record<string, string> = {endpoint_sec:'Endpoint', etch_rate_nm_min:'Etch rate', rf_reflected_w:'RF reflected', pressure_mtorr:'Pressure'}
export const units: Record<string, string> = {endpoint_sec:'sec', etch_rate_nm_min:'nm/min', rf_reflected_w:'W', pressure_mtorr:'mTorr'}
export const statuses: Record<string, string> = {
  QUEUED:'접수됨', RUNNING:'조사 중', SEARCH_STARTED:'근거 검색 중',
  ANALYSIS_STARTED:'수치 분석 중', REPORT_STARTED:'보고서 작성 중',
  WAITING_INPUT:'추가 정보 대기', WAITING_APPROVAL:'엔지니어 검토 대기',
  DONE:'완료', INCOMPLETE:'근거 부족', FAILED:'실패', REVIEWED:'검토됨', LOADING:'조사 불러오는 중'
}
export const terminal = new Set(['DONE', 'INCOMPLETE', 'FAILED'])

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
