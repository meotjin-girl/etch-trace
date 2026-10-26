import type { SessionAuth } from '@/auth'
import type { Transport } from './client'
import { createAuthenticatedHttp } from './authenticated-http'
import { actionRecord, approval, array, investigationSummary, liveInvestigation } from './live-models'

export interface CandidateSelection {
  readonly candidate_id: string
  readonly expected_revision: number
  readonly comment: string
}

export interface ActionInput {
  readonly content: string
  readonly result: string
}

export function createLiveApi(auth: SessionAuth, transport: Transport = {}) {
  const http = createAuthenticatedHttp(auth, transport)
  const root = '/api/investigations'
  const path = (id: string) => `${root}/${encodeURIComponent(id)}`
  return {
    async list(signal?: AbortSignal) {
      return array(await http.json(root, {signal})).map(investigationSummary)
    },
    async detail(id: string, signal?: AbortSignal) {
      return liveInvestigation(await http.json(path(id), {signal}))
    },
    async approve(id: string, selection: CandidateSelection, signal?: AbortSignal) {
      return approval(await http.json(`${path(id)}/approval`, {
        method:'POST', body:JSON.stringify(selection), signal,
      }))
    },
    /** Clears the chosen candidate so another can be chosen; refused once an action is recorded. */
    async cancelApproval(id: string, signal?: AbortSignal) {
      await http.response(`${path(id)}/approval`, {method:'DELETE', signal})
    },
    async recordAction(id: string, input: ActionInput, signal?: AbortSignal) {
      return actionRecord(await http.json(`${path(id)}/action`, {
        method:'POST', body:JSON.stringify(input), signal,
      }))
    },
  }
}
