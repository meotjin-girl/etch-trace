import type { SessionAuth } from '@/auth'
import type { Transport } from './client'
import { createAuthenticatedHttp } from './authenticated-http'
import { approval, array, investigationSummary, liveInvestigation } from './live-models'

export interface CandidateSelection {
  readonly candidate_id: string
  readonly expected_revision: number
  readonly comment: string
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
  }
}
