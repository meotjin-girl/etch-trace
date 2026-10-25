// Parser for the fixed alert text the backend sends to the agent (docs/agent-request.md).
// It mirrors agent/src/trace_agent/alert_text.py; unknown lines are ignored, never guessed.
import type { InvestigationSummary, LiveInvestigation } from '@/api/live-models'

export interface AlarmLine {
  readonly time: string
  readonly source: 'fdc' | 'equipment'
  readonly rule: string
  readonly sensor: string | null
  /** Numeric reading for equipment alarms, or the FDC rule value (z, σ, count…). */
  readonly value: number | null
  readonly unit: string
  readonly limit: number | null
  readonly detail: string
  readonly ocap: string
}
export interface SensorLine {
  readonly sensor: string
  readonly unit: string
  readonly mean: number | null
  readonly sd: number | null
  readonly points: readonly (number | null)[]
}
export interface ParsedAlert {
  readonly alarms: readonly AlarmLine[]
  readonly sensors: readonly SensorLine[]
  /** HH:MM:SS of the first sensor sample and the sampling step, when present. */
  readonly window: {readonly date: string, readonly start: string, readonly stepS: number} | null
}

const number = (text: string | undefined) => {
  if (text === undefined || text === '-') return null
  const value = Number(text)
  return Number.isFinite(value) ? value : null
}

function alarm(line: string): AlarmLine | null {
  const head = /^- (\d\d:\d\d:\d\d) (FDC|장비) (\S+) (.+) \(([^()]+)\)$/.exec(line)
  if (!head) return null
  const [, time, source, rule, body, ocap] = head as unknown as [string, string, string, string, string, string]
  if (source === '장비') {
    const equipment = /^(\S+)=(\S+) ?(\S*) \(한계 (\S+) ?\S*\)$/.exec(body)
    return {
      time, source:'equipment', rule, sensor:equipment?.[1] ?? null, value:number(equipment?.[2]),
      unit:equipment?.[3] ?? '', limit:number(equipment?.[4]), detail:body, ocap,
    }
  }
  const [sensor = '', expression = ''] = body.split(/ (.+)/)
  const value = /=(-?[\d.]+)/.exec(expression)
  return {
    time, source:'fdc', rule, sensor:sensor === '-' ? null : sensor, value:number(value?.[1]),
    unit:/ (\S+)$/.exec(expression)?.[1] ?? '', limit:null, detail:expression || body, ocap,
  }
}

function sensor(line: string): SensorLine | null {
  const match = /^- (\S+) \(([^,]*), 정상 (?:(-?[\d.]+)±([\d.]+)|-)\): (.*)$/.exec(line)
  if (!match) return null
  return {
    sensor:match[1]!, unit:match[2]!.trim(), mean:number(match[3]), sd:number(match[4]),
    points:match[5]!.trim().split(/\s+/).map(number),
  }
}

export function parseAlert(text: string): ParsedAlert {
  const alarms: AlarmLine[] = [], sensors: SensorLine[] = []
  let window: ParsedAlert['window'] = null
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    const head = /^\[센서\] (\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)~\S+ KST, (\d+)초 간격/.exec(line)
    if (head) { window = {date:head[1]!, start:head[2]!, stepS:Number(head[3])}; continue }
    const item = alarm(line) ?? sensor(line)
    if (item && 'rule' in item) alarms.push(item)
    else if (item) sensors.push(item)
  }
  return {alarms:alarms.sort((a, b) => a.time.localeCompare(b.time)), sensors, window}
}

const seconds = (clock: string) => {
  const [h = 0, m = 0, s = 0] = clock.split(':').map(Number)
  return h * 3600 + m * 60 + s
}

/** Sensor reading at an alarm time (nearest earlier sample) and the first reading of the run. */
export function readingAt(parsed: ParsedAlert, name: string, clock: string) {
  const series = parsed.sensors.find(item => item.sensor === name)
  if (!series) return null
  const step = parsed.window?.stepS || 5
  const index = parsed.window ? Math.floor((seconds(clock) - seconds(parsed.window.start)) / step) : -1
  const at = index >= 0 ? series.points[Math.min(index, series.points.length - 1)] ?? null : null
  const first = series.points.find(point => point !== null) ?? null
  return {series, value:at, first}
}

/** The alarm to headline: the first equipment interlock, otherwise the first FDC alert. */
export function primaryAlarm(parsed: ParsedAlert): AlarmLine | null {
  return parsed.alarms.find(item => item.source === 'equipment') ?? parsed.alarms[0] ?? null
}

export const ruleTitles: Readonly<Record<string, string>> = {
  PRESSURE_HIGH:'압력 상승', THROTTLE_SATURATION:'Throttle Valve 포화', RF_REFLECT_HIGH:'RF 반사 전력 상승',
  RF_SOURCE_LOW:'RF 출력 저하', MFC_FLOW_LOW:'SF6 가스 유량 저하', MFC_FLOW_HIGH:'O2 가스 유량 상승',
  HE_BACKSIDE_LOW:'후면 He 압력 저하', ESC_TEMP_HIGH:'ESC 온도 상승', OES_INTENSITY_DROP:'OES 발광 저하',
  PLASMA_IGNITION_DELAY:'플라즈마 점화 지연', FDC_WATCH:'정상 범위 이탈', PRESSURE_TREND:'압력 상승 추세',
  PRESSURE_OSC:'압력 진동', SENSOR_STALE:'센서 값 정지', MULTIVARIATE_FDC:'다중 계통 동시 이탈',
}
export const sensorLabels: Readonly<Record<string, string>> = {
  pressure_pv_mtorr:'압력', throttle_valve_pct:'Valve 위치', source_rf_pv_w:'Source RF',
  source_rf_reflected_w:'Source RF 반사', bias_rf_pv_w:'Bias RF', bias_rf_reflected_w:'Bias RF 반사',
  gas_sf6_pv_sccm:'SF6 유량', gas_o2_pv_sccm:'O2 유량', esc_temp_pv_c:'ESC 온도',
  backside_he_pv_torr:'후면 He', chiller_temp_pv_c:'칠러 온도', oes_intensity_au:'OES 강도',
}
export const ruleTitle = (rule: string) => ruleTitles[rule] ?? rule
export const sensorLabel = (name: string | null) => (name && sensorLabels[name]) || name || '-'

export type Stage = 'detected' | 'acting' | 'done'
export const stageLabels: Readonly<Record<Stage, string>> = {detected:'이상 탐지', acting:'조치 중', done:'조치 완료'}
type Staged = Pick<InvestigationSummary, 'approved_at' | 'action_recorded_at'>
export function stageOf(item: Staged | LiveInvestigation): Stage {
  if ('action' in item) return item.action ? 'done' : item.approval ? 'acting' : 'detected'
  return item.action_recorded_at ? 'done' : item.approved_at ? 'acting' : 'detected'
}

export const fixed = (value: number | null | undefined, digits = 3) =>
  value === null || value === undefined ? '-' : Number(value.toFixed(digits)).toString()
export const signed = (value: number | null | undefined, digits = 3) =>
  value === null || value === undefined ? '-' : `${value >= 0 ? '+' : ''}${fixed(value, digits)}`

/** What a card or header shows for an investigation: the headline alarm and its reading. */
export function headline(parsed: ParsedAlert) {
  const alarm = primaryAlarm(parsed)
  if (!alarm) return null
  const reading = alarm.sensor ? readingAt(parsed, alarm.sensor, alarm.time) : null
  const value = alarm.source === 'equipment' ? alarm.value : reading?.value ?? null
  const mean = reading?.series.mean ?? null
  return {
    alarm, value, mean, reading,
    unit:alarm.source === 'equipment' ? alarm.unit : reading?.series.unit ?? '',
    deviation:value !== null && mean !== null ? value - mean : null,
  }
}
