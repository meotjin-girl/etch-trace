import type { Candidate, InvestigationSummary, LiveInvestigation } from '@/api/live-models'

// Same grammar as backend/v1_alerts.py render() (docs/agent-request.md).
export const ALERT_TEXT = [
  '[경보] ETCH-07 / CH-B / Lot LOT-1 / Wafer W-1 / OX-120',
  '- 10:00:10 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)',
  '- 10:00:15 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.42 W (한계 37 W) (OCAP-ETCH-RF)',
  '[센서] 2026-10-23 10:00:00~10:00:20 KST, 5초 간격',
  '- source_rf_pv_w (W, 정상 900.375±4.837): 901.1 899 - 880.5 870',
  '- source_rf_reflected_w (W, 정상 5.364±0.590): 5.2 6.8 20 39.42 44.1',
].join('\n')

export const candidate: Candidate = {
  id:'00000000-0000-4000-8000-000000000011', cause:'RF matching drift', action:'Inspect matching network',
  rationale:'Reflected power increased', checks:['Compare chamber RF'], case_ids:['CASE-1'],
  doc_ids:['SOP-ETCH-12'], unknowns:['Maintenance log unavailable'],
}
export const detail: LiveInvestigation = {
  id:'00000000-0000-4000-8000-000000000001', thread_id:'00000000-0000-4000-8000-000000000001',
  alert:{tool_id:'ETCH-07', chamber_id:'CH-B', lot_id:'LOT-1', wafer_id:'W-1', recipe_id:'OX-120',
    source_text:ALERT_TEXT},
  summary:'RF reflected power investigation', candidates:[candidate], revision:3, approval:null, action:null,
  created_at:'2026-10-23T10:00:00Z', updated_at:'2026-10-23T10:01:00Z', demo:true,
}
export const summary: InvestigationSummary = {
  id:detail.id, thread_id:detail.thread_id, tool_id:detail.alert.tool_id, chamber_id:detail.alert.chamber_id,
  lot_id:detail.alert.lot_id, summary:detail.summary, revision:3, candidate_count:1,
  approved_at:null, action_recorded_at:null, created_at:detail.created_at, updated_at:detail.updated_at, demo:true,
}
export const snapshot = {
  revision:3, candidate, approved_by_id:'engineer-1', approved_by:'Engineer',
  approved_at:'2026-10-23T10:02:00Z', comment:'',
}
export const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {status})
export const values = (messages: unknown[]) => `event: values\ndata: ${JSON.stringify({messages})}\n\n`
export const sse = (text: string) => new Response(text, {headers:{'Content-Type':'text/event-stream'}})
