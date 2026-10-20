import { beforeEach, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Api } from '@/api/client'
import type { Task, TaskEvent } from '@/api/types'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { legacyRecords } from '@/stores/records'
import { useUiStore } from '@/stores/ui'

const name = '이엔지니어'
let calls: unknown[][]
let api: Record<string, any>

function stores() {
  return {investigation:useInvestigationStore(), identity:useIdentityStore(), ui:useUiStore()}
}

beforeEach(() => {
  setActivePinia(createPinia())
  calls = []
  api = {
    async list() { return [] },
    async detail(id: string) { return {id, status:'WAITING_INPUT', user_name:name, user_role:'engineer', events:[]} },
    async create(question: string) { calls.push(['create', question]); return {taskId:'task-1'} },
    async message(id: string, value: string) { calls.push(['message', id, value]) },
    async approval(id: string, body: unknown) { calls.push(['approval', id, body]) },
    stream() { return () => calls.push(['close']) },
  }
  useIdentityStore().api = api as unknown as Api
})

test('persisted clarification and its replay event yield one assistant follow-up', () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'WAITING_INPUT', messages:[{role:'assistant', text:'fixture-followup'}]}
  investigation.events = [{seq:1, type:'QUESTION', payload:{text:'fixture-followup'}}]
  expect(investigation.followUps).toHaveLength(0)
  investigation.events = [{seq:2, type:'QUESTION', payload:{text:'new-followup'}}]
  expect(investigation.followUps).toHaveLength(1)
})

test('review permissions: engineer waiting only, not worker/admin/legacy', () => {
  const {investigation, identity} = stores()
  const task: Task = {id:'a', status:'WAITING_APPROVAL'}
  expect(investigation.canReview(task)).toBe(true)
  for (const role of ['worker', 'admin'] as const) {
    identity.role = role
    expect(investigation.canReview(task)).toBe(false)
  }
  identity.role = 'engineer'
  expect(investigation.canReview({...task, legacy:true})).toBe(false)
  expect(investigation.canReview({id:'a', status:'DONE'})).toBe(false)
})

test('owner identity survives a role change and citations close the review dialog', () => {
  const {investigation, identity, ui} = stores()
  identity.role = 'worker'
  expect(investigation.isOwner({id:'a', status:'DONE', user_name:name, user_role:'engineer'})).toBe(true)
  expect(investigation.isOwner({id:'a', status:'DONE', user_name:'another-worker', user_role:'worker'})).toBe(false)
  investigation.openReview({id:'a', status:'WAITING_APPROVAL', report:{}})
  expect(investigation.review.task).not.toBeNull()
  ui.openEvidence('DOC#1')
  expect(investigation.review.task).toBeNull()
  expect(ui.highlightId).toBe('DOC#1')
})

test('old local records stay read-only and never become authoritative approvals', () => {
  const stored = JSON.stringify([{
    id:'OLD-1', context:{equipment:'ETCH-07', symptom:'fixture'},
    metrics:[], causes:[], documents:[{id:'DOC#1', title:'fixture', text:'fixture'}]
  }])
  vi.stubGlobal('localStorage', {getItem:(key: string) => key === 'etch-investigation-records-v1' ? stored : null})
  const [record] = legacyRecords()
  vi.unstubAllGlobals()
  expect(record!.legacy).toBe(true)
  expect(record!.legacyId).toBe('OLD-1')
  expect(stores().investigation.canReview(record)).toBe(false)
  expect(record!.report!.documents![0]!.id).toBe('DOC#1')
})

test('send creates once, continues only owned waiting task, reset clears state', async () => {
  const {investigation} = stores()
  investigation.draft = '새 질문'
  await investigation.submitQuestion()
  expect(calls[0]).toEqual(['create', '새 질문'])
  investigation.draft = '추가'
  await investigation.submitQuestion()
  expect(calls.find(call => call[0] === 'message')).toEqual(['message', 'task-1', '추가'])
  investigation.reset()
  expect(investigation.task).toBeNull()
  expect(investigation.after).toBe(0)
})

test('reset aborts in-flight requests', async () => {
  const {investigation} = stores()
  let signal: AbortSignal | undefined
  api.create = (_: string, s: AbortSignal) => { signal = s; return new Promise(() => {}) }
  investigation.draft = '질문'
  investigation.submitQuestion()
  investigation.reset()
  expect(signal!.aborted).toBe(true)
})

test('review sends server actor metadata and revise requires comment', async () => {
  const {investigation} = stores()
  investigation.openReview({id:'a', status:'WAITING_APPROVAL', report:{}})
  expect(await investigation.submitReview('revise')).toBe(false)
  expect(calls).toHaveLength(0)
  Object.assign(investigation.review, {comment:'다시 확인', time:'2026-10-20T10:00', lot:'LOT-1'})
  await investigation.submitReview('revise')
  const body = calls.find(item => item[0] === 'approval')![2] as Record<string, string>
  expect(body.action).toBe('revise')
  expect(body.comment).toBe('다시 확인')
  expect(body.lot_id).toBe('LOT-1')
  expect(body.event_time!.endsWith('Z')).toBe(true)
  expect(body).not.toHaveProperty('by')
})

test('detail status survives replay of an old approval after revision', async () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'RUNNING'}
  investigation.events = [{seq:1, type:'APPROVAL_REQUIRED', payload:{}}]
  investigation.after = 1
  api.detail = async () => ({id:'a', status:'RUNNING', events:investigation.events})
  await investigation.syncTask()
  expect(investigation.task!.status).toBe('RUNNING')
})

test('late live callbacks cannot bleed into a new investigation', () => {
  const {investigation} = stores()
  let receive: (event: TaskEvent) => void = () => {}
  api.stream = (_id: string, _after: number, handlers: {onEvent: typeof receive}) => { receive = handlers.onEvent; return () => {} }
  investigation.task = {id:'a', status:'RUNNING'}
  investigation.connectStream()
  investigation.reset()
  receive({seq:1, type:'DONE', payload:{report:{summary:'old'}}})
  expect(investigation.task).toBeNull()
})

test('pending create disables duplicate sends without timing waits', async () => {
  const {investigation} = stores()
  let accept: (value: {taskId: string}) => void = () => {}
  api.create = (question: string) => {
    calls.push(['create', question])
    return new Promise(resolve => { accept = resolve })
  }
  investigation.draft = '한 번만'
  const pending = investigation.submitQuestion()
  await investigation.submitQuestion()
  expect(calls.filter(call => call[0] === 'create')).toHaveLength(1)
  accept({taskId:'one'})
  await pending
})

test('newer detail requests win even if older requests finish later', async () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'RUNNING'}
  const responses: ((task: Task) => void)[] = []
  api.detail = () => new Promise(resolve => responses.push(resolve))
  const first = investigation.syncTask()
  const second = investigation.syncTask()
  responses[1]!({id:'a', status:'DONE', events:[]})
  await second
  responses[0]!({id:'a', status:'RUNNING', events:[]})
  await first
  expect(investigation.task!.status).toBe('DONE')
})

test('live events arriving during a detail request retain their newer state', async () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'RUNNING'}
  let complete: (task: Task) => void = () => {}
  api.detail = () => new Promise(resolve => { complete = resolve })
  const pending = investigation.syncTask()
  investigation.after = 2
  investigation.events = [{seq:2, type:'APPROVAL_REQUIRED', payload:{report:{summary:'new'}}}]
  investigation.task.status = 'WAITING_APPROVAL'
  investigation.task.report = {summary:'new'}
  complete({id:'a', status:'RUNNING', events:[]})
  await pending
  expect(investigation.task!.status).toBe('WAITING_APPROVAL')
  expect(investigation.task!.report!.summary).toBe('new')
})

test('progress step follows backend events only', () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'RUNNING'}
  expect(investigation.step).toBe(1)
  investigation.applyEvents([{seq:1, type:'SEARCH_STARTED', payload:{}}, {seq:2, type:'ANALYSIS_STARTED', payload:{}}])
  expect(investigation.step).toBe(3)
  investigation.applyEvents([{seq:3, type:'QUESTION', payload:{text:'?'}}])
  expect(investigation.task!.status).toBe('WAITING_INPUT')
})
