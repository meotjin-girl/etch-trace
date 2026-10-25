import { ApiError } from './client'

export interface Candidate {
  readonly id: string
  readonly cause: string
  readonly action: string
  readonly rationale: string
  readonly checks: readonly string[]
  readonly case_ids: readonly string[]
  readonly doc_ids: readonly string[]
  readonly unknowns: readonly string[]
}
export interface Approval {
  readonly revision: number
  readonly candidate: Candidate
  readonly approved_by_id: string
  readonly approved_by: string
  readonly approved_at: string
  readonly comment: string
}
export interface ActionRecord {
  readonly content: string
  readonly result: string
  readonly recorded_by_id: string
  readonly recorded_by: string
  readonly recorded_at: string
}
export interface Alert {
  readonly tool_id: string
  readonly chamber_id: string
  readonly lot_id: string
  readonly wafer_id: string
  readonly recipe_id: string
  readonly source_text: string
}
export interface InvestigationSummary {
  readonly id: string
  readonly thread_id: string
  readonly tool_id: string
  readonly chamber_id: string
  readonly lot_id: string
  readonly summary: string
  readonly revision: number
  readonly candidate_count: number
  readonly approved_at: string | null
  readonly action_recorded_at: string | null
  readonly created_at: string
  readonly updated_at: string
  readonly demo: true
}
export interface LiveInvestigation {
  readonly id: string
  readonly thread_id: string
  readonly alert: Alert
  readonly summary: string
  readonly candidates: readonly Candidate[]
  readonly revision: number
  readonly approval: Approval | null
  readonly action: ActionRecord | null
  readonly created_at: string
  readonly updated_at: string
  readonly demo: true
}

// The project uses small boundary parsers rather than a schema dependency.
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
export function object(value: unknown): Record<string, unknown> {
  if (!isObject(value)) throw new ApiError('서버 응답 객체가 올바르지 않습니다.')
  return value
}
export function string(value: unknown): string {
  if (typeof value !== 'string') throw new ApiError('서버 응답 문자열이 올바르지 않습니다.')
  return value
}
export function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new ApiError('서버 응답 목록이 올바르지 않습니다.')
  return value
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new ApiError('서버 응답 버전이 올바르지 않습니다.')
  return value
}
function demo(value: unknown): true {
  if (value !== true) throw new ApiError('데모 조사 응답이 올바르지 않습니다.')
  return value
}
export function candidate(value: unknown): Candidate {
  const row = object(value)
  return {
    id:string(row.id), cause:string(row.cause), action:string(row.action), rationale:string(row.rationale),
    checks:array(row.checks).map(string), case_ids:array(row.case_ids).map(string),
    doc_ids:array(row.doc_ids).map(string), unknowns:array(row.unknowns).map(string),
  }
}
export function approval(value: unknown): Approval {
  const row = object(value)
  return {
    revision:integer(row.revision), candidate:candidate(row.candidate),
    approved_by_id:string(row.approved_by_id), approved_by:string(row.approved_by),
    approved_at:string(row.approved_at), comment:string(row.comment),
  }
}
export function actionRecord(value: unknown): ActionRecord {
  const row = object(value)
  return {
    content:string(row.content), result:string(row.result), recorded_by_id:string(row.recorded_by_id),
    recorded_by:string(row.recorded_by), recorded_at:string(row.recorded_at),
  }
}
const optionalString = (value: unknown) => value === null || value === undefined ? null : string(value)
export function investigationSummary(value: unknown): InvestigationSummary {
  const row = object(value)
  return {
    id:string(row.id), thread_id:string(row.thread_id), tool_id:string(row.tool_id),
    chamber_id:string(row.chamber_id), lot_id:string(row.lot_id), summary:string(row.summary),
    revision:integer(row.revision), candidate_count:integer(row.candidate_count),
    approved_at:row.approved_at === null ? null : string(row.approved_at),
    action_recorded_at:optionalString(row.action_recorded_at),
    created_at:string(row.created_at), updated_at:string(row.updated_at), demo:demo(row.demo),
  }
}
export function liveInvestigation(value: unknown): LiveInvestigation {
  const row = object(value), alert = object(row.alert)
  return {
    id:string(row.id), thread_id:string(row.thread_id), summary:string(row.summary),
    candidates:array(row.candidates).map(candidate), revision:integer(row.revision),
    approval:row.approval === null ? null : approval(row.approval),
    action:row.action === null || row.action === undefined ? null : actionRecord(row.action),
    created_at:string(row.created_at), updated_at:string(row.updated_at), demo:demo(row.demo),
    alert:{
      tool_id:string(alert.tool_id), chamber_id:string(alert.chamber_id), lot_id:string(alert.lot_id),
      wafer_id:string(alert.wafer_id), recipe_id:string(alert.recipe_id), source_text:string(alert.source_text),
    },
  }
}
