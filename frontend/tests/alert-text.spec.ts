import { expect, test } from 'vitest'
import { headline, parseAlert, readingAt, stageOf } from '@/lib/alert-text'
import { ALERT_TEXT, detail, summary } from './live-fixtures'

test('alert text parses alarms, sensor series and the equipment headline', () => {
  const parsed = parseAlert(ALERT_TEXT)
  expect(parsed.window).toEqual({date:'2026-10-23', start:'10:00:00', stepS:5})
  expect(parsed.alarms.map(alarm => [alarm.source, alarm.rule, alarm.sensor, alarm.value, alarm.ocap])).toEqual([
    ['fdc', 'FDC_WATCH', 'source_rf_reflected_w', 4.1, 'OCAP-ETCH-RF'],
    ['equipment', 'RF_REFLECT_HIGH', 'source_rf_reflected_w', 39.42, 'OCAP-ETCH-RF'],
  ])
  expect(parsed.alarms[1]).toMatchObject({unit:'W', limit:37})
  expect(parsed.sensors[0]!.points).toEqual([901.1, 899, null, 880.5, 870])
  // 10:00:15 is the 4th 5-second sample; missing samples stay null.
  expect(readingAt(parsed, 'source_rf_pv_w', '10:00:15')).toMatchObject({value:880.5, first:901.1})
  expect(readingAt(parsed, 'source_rf_pv_w', '10:00:10')?.value).toBeNull()
  const head = headline(parsed)!
  expect(head.alarm.rule).toBe('RF_REFLECT_HIGH')
  expect(head.value).toBe(39.42)
  expect(head.deviation).toBeCloseTo(39.42 - 5.364)
})

test('unknown lines and FDC rules without a sensor are tolerated', () => {
  const parsed = parseAlert('[경보] T / C / Lot L / Wafer W / R\n- 09:00:00 FDC MULTIVARIATE_FDC - 계통=2 (SOP-ETCH-12)\nnoise')
  expect(parsed.alarms).toEqual([expect.objectContaining({rule:'MULTIVARIATE_FDC', sensor:null, value:2})])
  expect(headline(parsed)?.value).toBeNull()
  expect(parsed.sensors).toEqual([])
})

test('stage is detected, acting after approval, done after the action record', () => {
  expect(stageOf(summary)).toBe('detected')
  expect(stageOf({...summary, approved_at:'x'})).toBe('acting')
  expect(stageOf({...summary, approved_at:'x', action_recorded_at:'y'})).toBe('done')
  expect(stageOf(detail)).toBe('detected')
})
