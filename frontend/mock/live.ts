// In-memory live investigations + Agent Server thread mock for `npm run dev:mock`.
// Alert texts follow backend/v1_alerts.py render(); all values are synthetic.
import { randomUUID } from 'node:crypto'

type Row = Record<string, unknown>
interface Investigation extends Row {
  id: string
  thread_id: string
  alert: {tool_id: string, chamber_id: string, lot_id: string, wafer_id: string, recipe_id: string, source_text: string}
  summary: string
  candidates: Row[]
  revision: number
  approval: Row | null
  action: Row | null
  created_at: string
  updated_at: string
  demo: true
}

const series = (name: string, unit: string, mean: number, sd: number, values: (number | null)[]) =>
  `- ${name} (${unit}, 정상 ${mean.toFixed(3)}±${sd.toFixed(3)}): ${values.map(v => v === null ? '-' : v).join(' ')}`
const ramp = (from: number, to: number, n = 26, start = 10) =>
  Array.from({length:n}, (_, i) => Number((i < start ? from + (i % 3 - 1) * 0.08 : from + (to - from) * (i - start) / (n - 1 - start)).toFixed(3)))

function text(tool: string, chamber: string, lot: string, alarms: string[], rows: string[]) {
  return [`[경보] ${tool} / ${chamber} / Lot ${lot} / Wafer ${lot}-W01 / RCP-OX-ETCH-EDU-01`, ...alarms,
    '[센서] 2026-10-26 08:35:00~08:37:05 KST, 5초 간격', ...rows].join('\n')
}
const common = (overrides: Record<string, string> = {}) => [
  overrides.pressure ?? series('pressure_pv_mtorr', 'mTorr', 25.013, 0.163, ramp(25.0, 25.2)),
  overrides.throttle ?? series('throttle_valve_pct', '%', 44.003, 0.655, ramp(44.2, 44.4)),
  overrides.rf ?? series('source_rf_pv_w', 'W', 900.375, 4.837, ramp(900, 902)),
  overrides.reflect ?? series('source_rf_reflected_w', 'W', 5.364, 0.59, ramp(5.3, 5.6)),
  overrides.sf6 ?? series('gas_sf6_pv_sccm', 'sccm', 99.975, 0.429, ramp(99.9, 100.1)),
  series('esc_temp_pv_c', 'degC', 19.978, 0.144, ramp(19.98, 20.02)),
  series('oes_intensity_au', 'au', 5102.127, 44.067, ramp(5100, 5090)),
]
const candidate = (cause: string, action: string, rationale: string, checks: string[], docs: string[], unknowns: string[]) =>
  ({id:randomUUID(), cause, action, rationale, checks, case_ids:[], doc_ids:docs, unknowns})

function seed(): Investigation[] {
  const now = Date.now()
  const make = (minutesAgo: number, tool: string, chamber: string, lot: string, summary: string,
    alertText: string, candidates: Row[]): Investigation => {
    const id = randomUUID(), at = new Date(now - minutesAgo * 60_000).toISOString()
    return {id, thread_id:id, alert:{tool_id:tool, chamber_id:chamber, lot_id:lot, wafer_id:`${lot}-W01`,
      recipe_id:'RCP-OX-ETCH-EDU-01', source_text:alertText}, summary, candidates, revision:1,
      approval:null, action:null, created_at:at, updated_at:at, demo:true}
  }
  const pressure = make(4, 'ETCH-01', 'CH-B', 'SIMLOT-20261026-1B083500', '챔버 압력 상승 조사',
    text('ETCH-01', 'CH-B', 'SIMLOT-20261026-1B083500', [
      '- 08:36:05 FDC FDC_WATCH pressure_pv_mtorr z=6.2 (OCAP-ETCH-PRS)',
      '- 08:36:15 FDC PRESSURE_TREND pressure_pv_mtorr 예측=33.1 mTorr (OCAP-ETCH-PRS)',
      '- 08:36:40 장비 PRESSURE_HIGH pressure_pv_mtorr=30.099 mTorr (한계 30 mTorr) (OCAP-ETCH-PRS)',
    ], common({pressure:series('pressure_pv_mtorr', 'mTorr', 25.013, 0.163, ramp(25.0, 37.2)),
      throttle:series('throttle_valve_pct', '%', 44.003, 0.655, ramp(44.24, 52.1))})),
    [candidate('압력 제어·Valve 보상 변화', '같은 recipe·step의 이전 Run과 압력 오차·Valve 응답 비교',
      '압력이 정상 평균보다 5.1 mTorr 높고 Valve 위치도 초기보다 2.7%p 이동했습니다. 펌프·foreline 신호가 없어 제어계 이상을 확정할 수 없습니다.',
      ['같은 recipe·step의 이전 Run 비교', 'pump / foreline 신호 확인'], ['OCAP-ETCH-PRS'], ['pump·foreline 데이터 없음']),
    candidate('추가 점검: 압력계 신뢰성', '보조 gauge와 교차 확인', '압력 상승은 확인되나 보조 gauge 데이터가 없습니다.',
      ['보조 gauge 값 비교'], ['OCAP-ETCH-PRS'], ['보조 gauge 데이터 없음'])])
  const rf = make(9, 'ETCH-02', 'CH-A', 'SIMLOT-20261026-2A083000', 'RF 반사 전력 상승 조사',
    text('ETCH-02', 'CH-A', 'SIMLOT-20261026-2A083000', [
      '- 08:35:55 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)',
      '- 08:36:20 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.42 W (한계 37 W) (OCAP-ETCH-RF)',
    ], common({reflect:series('source_rf_reflected_w', 'W', 5.364, 0.59, ramp(5.3, 44.1)),
      rf:series('source_rf_pv_w', 'W', 900.375, 4.837, ramp(900, 872))})),
    [candidate('RF 매칭 네트워크 드리프트', '매칭 네트워크 tuning 위치와 반사 전력 이력 확인',
      '반사 전력이 39.42 W로 한계 37 W를 넘었고 같은 시점 Source RF 출력이 약 28 W 떨어졌습니다.',
      ['매칭 tuning 위치 확인', '같은 챔버 이전 Run의 반사 전력 비교'], ['OCAP-ETCH-RF'], ['정비 이력 없음'])])
  const gas = make(30, 'ETCH-02', 'CH-B', 'SIMLOT-20261026-2B080500', 'SF6 가스 유량 저하 조사',
    text('ETCH-02', 'CH-B', 'SIMLOT-20261026-2B080500', [
      '- 08:36:30 장비 MFC_FLOW_LOW gas_sf6_pv_sccm=86.298 sccm (한계 87 sccm) (OCAP-ETCH-GAS)',
    ], common({sf6:series('gas_sf6_pv_sccm', 'sccm', 99.975, 0.429, ramp(99.9, 77.4))})),
    [candidate('SF6 MFC 유량 저하', 'MFC readback과 setpoint, 가스 라인 압력 확인',
      'SF6 유량이 86.3 sccm으로 한계 87 sccm 아래로 내려갔고 OES 강도도 함께 감소했습니다.',
      ['MFC readback·setpoint 비교', '가스 공급 라인 압력 확인'], ['OCAP-ETCH-GAS'], [])])
  gas.approval = {revision:1, candidate:gas.candidates[0], approved_by_id:'mock-user', approved_by:'목업 사용자',
    approved_at:new Date(now - 20 * 60_000).toISOString(), comment:''}
  const esc = make(80, 'ETCH-03', 'CH-A', 'SIMLOT-20261026-3A071500', 'ESC 온도 상승 조사',
    text('ETCH-03', 'CH-A', 'SIMLOT-20261026-3A071500', [
      '- 08:36:35 장비 ESC_TEMP_HIGH esc_temp_pv_c=25.064 degC (한계 25 degC) (OCAP-ETCH-TMP)',
    ], common()), [candidate('칠러 냉각 능력 저하', '칠러 유량·온도 확인', 'ESC 온도가 25 °C를 넘었습니다.',
      ['칠러 유량 확인'], ['OCAP-ETCH-TMP'], [])])
  esc.approval = {revision:1, candidate:esc.candidates[0], approved_by_id:'mock-user', approved_by:'목업 사용자',
    approved_at:new Date(now - 70 * 60_000).toISOString(), comment:''}
  esc.action = {content:'칠러 필터 교체 후 유량 재측정', result:'ESC 온도 20.1 °C로 복귀, 다음 Run 정상',
    recorded_by_id:'mock-user', recorded_by:'목업 사용자', recorded_at:new Date(now - 60 * 60_000).toISOString()}
  return [pressure, rf, gas, esc]
}

export class LiveError extends Error {
  constructor(readonly status: number, message: string) { super(message) }
}

export function createLiveMock() {
  const items = seed()
  const threads = new Map(items.map(item => [item.thread_id, [
    {type:'human', id:randomUUID(), content:item.alert.source_text},
    {type:'ai', id:randomUUID(), content:`${item.summary} 결과, 원인 후보 ${item.candidates.length}개를 정리했습니다. 수치는 경보 센서 구간에서 계산했고 원인은 확인 전 가설입니다.`},
  ]]))
  const find = (id: string) => {
    const item = items.find(entry => entry.id === id)
    if (!item) throw new LiveError(404, 'Investigation not found')
    return item
  }
  const touch = (item: Investigation) => { item.updated_at = new Date().toISOString() }
  return {
    list: () => [...items].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).map(item => ({
      id:item.id, thread_id:item.thread_id, tool_id:item.alert.tool_id, chamber_id:item.alert.chamber_id,
      lot_id:item.alert.lot_id, summary:item.summary, revision:item.revision, candidate_count:item.candidates.length,
      approved_at:(item.approval?.approved_at as string | undefined) ?? null,
      action_recorded_at:(item.action?.recorded_at as string | undefined) ?? null,
      created_at:item.created_at, updated_at:item.updated_at, demo:true,
    })),
    detail: find,
    approve(id: string, body: Row) {
      const item = find(id)
      if (item.approval) throw new LiveError(409, 'Investigation already approved')
      const chosen = item.candidates.find(entry => entry.id === body.candidate_id)
      if (!chosen) throw new LiveError(422, 'Candidate does not belong to this revision')
      item.approval = {revision:item.revision, candidate:chosen, approved_by_id:'mock-user', approved_by:'목업 사용자',
        approved_at:new Date().toISOString(), comment:String(body.comment ?? '')}
      touch(item)
      return item.approval
    },
    cancelApproval(id: string) {
      const item = find(id)
      if (!item.approval || item.action) throw new LiveError(409, 'Not approved or action already recorded')
      item.approval = null
      touch(item)
    },
    recordAction(id: string, body: Row) {
      const item = find(id)
      if (!item.approval || item.action) throw new LiveError(409, 'Approve first or already recorded')
      const content = String(body.content ?? '').trim(), result = String(body.result ?? '').trim()
      if (!content || !result) throw new LiveError(422, 'content and result are required')
      item.action = {content, result, recorded_by_id:'mock-user', recorded_by:'목업 사용자', recorded_at:new Date().toISOString()}
      touch(item)
      return item.action
    },
    state: (threadId: string) => ({values:{messages:threads.get(threadId) ?? []}}),
    ask(threadId: string, question: string) {
      const messages = threads.get(threadId)
      if (!messages) throw new LiveError(404, 'Thread not found')
      messages.push({type:'human', id:randomUUID(), content:question},
        {type:'ai', id:randomUUID(), content:`(목업 응답) "${question}"에 대해: 경보 시점 센서값과 연결 문서를 기준으로 보면 후보 1이 가장 유력하지만, 현장 확인 전에는 확정할 수 없습니다.`})
      return `event: values\ndata: ${JSON.stringify({messages})}\n\n`
    },
  }
}
