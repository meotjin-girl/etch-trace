import type { Candidate, InvestigationSummary, LiveInvestigation } from '@/api/live-models'

export const candidate: Candidate = {
  id:'00000000-0000-4000-8000-000000000011', cause:'RF matching drift', action:'Inspect matching network',
  rationale:'Reflected power increased', checks:['Compare chamber RF'], case_ids:['CASE-1'],
  doc_ids:['SOP-ETCH-12'], unknowns:['Maintenance log unavailable'],
}
export const detail: LiveInvestigation = {
  id:'00000000-0000-4000-8000-000000000001', thread_id:'00000000-0000-4000-8000-000000000001',
  alert:{tool_id:'ETCH-07', chamber_id:'CH-B', lot_id:'LOT-1', wafer_id:'W-1', recipe_id:'OX-120',
    source_text:'2026-10-23T10:00:00Z reflected power 29 W'},
  summary:'RF reflected power investigation', candidates:[candidate], revision:3, approval:null,
  created_at:'2026-10-23T10:00:00Z', updated_at:'2026-10-23T10:01:00Z', demo:true,
}
export const summary: InvestigationSummary = {
  id:detail.id, thread_id:detail.thread_id, tool_id:detail.alert.tool_id, chamber_id:detail.alert.chamber_id,
  lot_id:detail.alert.lot_id, summary:detail.summary, revision:3, candidate_count:1,
  approved_at:null, created_at:detail.created_at, updated_at:detail.updated_at, demo:true,
}
export const snapshot = {
  revision:3, candidate, approved_by_id:'engineer-1', approved_by:'Engineer',
  approved_at:'2026-10-23T10:02:00Z', comment:'',
}
export const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {status})
export const values = (messages: unknown[]) => `event: values\ndata: ${JSON.stringify({messages})}\n\n`
export const sse = (text: string) => new Response(text, {headers:{'Content-Type':'text/event-stream'}})
