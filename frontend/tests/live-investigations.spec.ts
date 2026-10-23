import { beforeEach, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createLiveApi } from '@/api/live-investigations'
import { createAgentApi, type AgentRun } from '@/api/agent-server'
import type { LiveInvestigation } from '@/api/live-models'
import { useIdentityStore } from '@/stores/identity'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'
import { candidate, detail, json, snapshot, sse, values } from './live-fixtures'

beforeEach(() => setActivePinia(createPinia()))

function setup() {
  let record: LiveInvestigation = {...detail}
  let runs: AgentRun[] = []
  let history: unknown[] = [{type:'human', id:'initial', content:'Initial alert'}]
  const calls: {url: string, init: RequestInit}[] = []
  let intercept: (url: string, init: RequestInit) => Promise<Response | undefined> = async () => undefined
  const fetcher: typeof fetch = async (input, init = {}) => {
    const url = String(input)
    calls.push({url, init})
    const intercepted = await intercept(url, init)
    if (intercepted) return intercepted
    if (url.endsWith('/approval')) { record = {...record, approval:snapshot}; return json(snapshot) }
    if (url.startsWith('/api/investigations/')) return json(record)
    if (url.endsWith('/state')) return json({values:{messages:history}})
    if (url.includes('/runs?')) return json(runs)
    if (url.includes('/stream')) {
      record = {...record, revision:4, candidates:[{...candidate, cause:'Updated after follow-up'}]}
      history = [...history, {type:'human', id:'follow-up', content:'follow-up'}, {type:'ai', id:'answer', content:'Updated answer'}]
      runs = [{run_id:'run-1', status:'success'}]
      return sse(values(history))
    }
    throw new Error(`Unexpected request ${url}`)
  }
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  const auth = {getToken:async () => 'token', invalidate() {}}
  identity.liveApi = createLiveApi(auth, {fetch:fetcher})
  identity.agentApi = createAgentApi(auth, {fetch:fetcher})
  return {
    identity, store:useLiveInvestigationsStore(), calls,
    setRecord(value: LiveInvestigation) { record = value },
    setRuns(value: AgentRun[]) { runs = value },
    intercept(value: typeof intercept) { intercept = value },
  }
}

test('candidate approval uses stable ID and post-approval conversation preserves the snapshot', async () => {
  // Given candidates reordered independently of their identity.
  const {store, calls, setRecord} = setup()
  setRecord({...detail, candidates:[{...candidate, id:'another-id', cause:'Other'}, candidate]})
  await store.open(detail.id)
  // When the second candidate is approved and the same thread receives a follow-up.
  await store.approve(candidate.id)
  store.draft = 'follow-up'
  await store.send()
  // Then the approval is unchanged while the live candidate and conversation advance.
  const approval = calls.find(call => call.url.endsWith('/approval'))
  expect(JSON.parse(String(approval?.init.body))).toEqual({candidate_id:candidate.id, expected_revision:3, comment:''})
  expect(store.detail?.approval).toEqual(snapshot)
  expect(store.detail?.candidates[0]?.cause).toBe('Updated after follow-up')
  expect(store.detail?.revision).toBe(4)
  expect(store.messages.at(-1)?.text).toBe('Updated answer')
  expect(store.canSend).toBe(true)
  expect(store.draft).toBe('')
  expect(calls.filter(call => call.init.method === 'POST').map(call => call.url)).toEqual([
    `/api/investigations/${detail.id}/approval`, `/agent/threads/${detail.thread_id}/runs/stream`,
  ])
})

test('reopening a busy thread joins its active run without submitting another run', async () => {
  // Given a busy thread with a deferred join response.
  const {store, calls, setRuns, intercept} = setup()
  const joined = Promise.withResolvers<void>(), response = Promise.withResolvers<Response>()
  setRuns([{run_id:'active-run', status:'running'}])
  intercept(async url => {
    if (!url.includes('/active-run/stream')) return undefined
    joined.resolve()
    return response.promise
  })
  // When opening the record, observe the join before completing it.
  const opening = store.open(detail.id)
  await joined.promise
  expect(store.busy).toBe(true)
  expect(store.canSend).toBe(false)
  setRuns([{run_id:'active-run', status:'success'}])
  response.resolve(sse(values([{type:'ai', content:'completed'}])))
  await opening
  // Then no mutation was sent and backend detail was refreshed after the run.
  expect(calls.some(call => call.init.method === 'POST')).toBe(false)
  expect(calls.filter(call => call.url === `/api/investigations/${detail.id}`)).toHaveLength(2)
  expect(store.busy).toBe(false)
  expect(store.error).toBe('')
})

test('a collaborator starting between preflight and send is joined after 409 and the unsent draft remains', async () => {
  // Given an idle thread whose next POST races with another collaborator.
  const {store, calls, intercept, setRuns} = setup()
  await store.open(detail.id)
  intercept(async (url, init) => {
    if (url.endsWith('/runs/stream') && init.method === 'POST') {
      setRuns([{run_id:'collaborator', status:'running'}])
      return json({}, 409)
    }
    return undefined
  })
  store.draft = 'Do not lose this'
  // When the server rejects the concurrent run.
  await store.send()
  // Then only the collaborator run is joined; the draft is not falsely marked sent.
  expect(calls.filter(call => call.init.method === 'POST')).toHaveLength(1)
  expect(calls.some(call => call.url.includes('/collaborator/stream'))).toBe(true)
  expect(store.draft).toBe('Do not lose this')
  expect(store.detail?.revision).toBe(4)
})

test('approval conflicts refresh the authoritative snapshot and never retry approval automatically', async () => {
  // Given an unapproved record that a collaborator approves first.
  const {store, calls, intercept, setRecord} = setup()
  await store.open(detail.id)
  intercept(async url => {
    if (!url.endsWith('/approval')) return undefined
    setRecord({...detail, approval:snapshot, revision:4})
    return json({}, 409)
  })
  // When attempting approval with the old revision.
  await store.approve(candidate.id)
  await store.approve(candidate.id)
  // Then the immutable winner is displayed and no second POST occurs.
  expect(store.detail?.approval).toEqual(snapshot)
  expect(store.detail?.revision).toBe(4)
  expect(store.error).not.toBe('')
  expect(calls.filter(call => call.url.endsWith('/approval'))).toHaveLength(1)
  expect(store.canSend).toBe(true)
})

test('duplicate sends are blocked while a run is active and stream failure still refreshes business detail', async () => {
  // Given a pending stream and the next persisted business revision.
  const {store, calls, intercept, setRecord} = setup()
  await store.open(detail.id)
  const started = Promise.withResolvers<void>(), response = Promise.withResolvers<Response>()
  intercept(async url => {
    if (!url.endsWith('/runs/stream')) return undefined
    started.resolve()
    return response.promise
  })
  store.draft = 'follow-up'
  // When two submissions occur before the first stream completes.
  const sending = store.send()
  await started.promise
  await store.send()
  setRecord({...detail, revision:4})
  response.resolve(sse('event: error\ndata: {"error":"failed"}\n\n'))
  await sending
  // Then there is one run and the refreshed detail is retained alongside the error.
  expect(calls.filter(call => call.init.method === 'POST')).toHaveLength(1)
  expect(store.detail?.revision).toBe(4)
  expect(store.error).not.toBe('')
  expect(store.busy).toBe(false)
})

test('logout aborts an in-flight opening and stale data cannot restore private workspace state', async () => {
  // Given a backend detail response held across logout.
  const {store, identity, intercept} = setup()
  const started = Promise.withResolvers<void>(), response = Promise.withResolvers<Response>()
  let signal: AbortSignal | null | undefined
  intercept(async (url, init) => {
    if (!url.startsWith('/api/investigations/')) return undefined
    signal = init.signal
    started.resolve()
    return response.promise
  })
  const opening = store.open(detail.id)
  await started.promise
  // When logging out before the response arrives.
  await identity.logout()
  response.resolve(json(detail))
  await opening
  // Then cancellation and generation identity both protect the cleared state.
  expect(signal?.aborted).toBe(true)
  expect(store.detail).toBeNull()
  expect(store.messages).toEqual([])
  expect(store.draft).toBe('')
  expect(store.loading).toBe(false)
})
