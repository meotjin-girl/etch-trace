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
  useIdentityStore().status = 'authenticated'
  useIdentityStore().name = name
  useIdentityStore().subject = 'account-1'
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

test('chat follows saved event order across question, answer, report and judgement', () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'WAITING_INPUT', question:'처음 질문', user_name:name,
    messages:[{role:'assistant', text:'persisted copy is not drawn twice'}]}
  investigation.events = [
    {seq:1, type:'QUEUED', payload:{}}, {seq:2, type:'RUNNING', payload:{}},
    {seq:3, type:'QUESTION', payload:{text:'장비는?'}}, {seq:4, type:'MESSAGE', payload:{text:'ETCH-07'}},
    {seq:5, type:'APPROVAL_REQUIRED', payload:{report:{summary:'r1'}}},
    {seq:6, type:'REVIEWED', payload:{action:'revise', comment:'RF 보강'}},
    {seq:7, type:'QUESTION', payload:{text:'기록할 정보?', options:['건너뛰기']}},
  ]
  expect(investigation.chat.map(item => [item.role, item.kind, item.text ?? item.report?.summary])).toEqual([
    ['user', 'text', '처음 질문'], ['assistant', 'question', '장비는?'], ['user', 'text', 'ETCH-07'],
    ['assistant', 'report', 'r1'], ['user', 'text', '미승인 · RF 보강'], ['assistant', 'question', '기록할 정보?'],
  ])
  expect(investigation.pending).toEqual({seq:7, options:['건너뛰기'], decision:false})
})

test('quick replies allow collaborators on the latest pending prompt, decisions default to 승인/미승인', () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'WAITING_INPUT', user_name:name}
  investigation.events = [{seq:1, type:'QUESTION', payload:{text:'?'}}]
  expect(investigation.pending).toBeNull()
  investigation.task = {id:'a', status:'WAITING_INPUT', user_name:'다른 사람'}
  investigation.events = [{seq:1, type:'QUESTION', payload:{text:'?', options:['예']}}]
  expect(investigation.pending).toEqual({seq:1, options:['예'], decision:false})
  investigation.task = {id:'a', status:'WAITING_APPROVAL', user_name:name}
  investigation.events = [{seq:2, type:'APPROVAL_REQUIRED', payload:{report:{}}}]
  expect(investigation.pending).toEqual({seq:2, options:['승인', '미승인'], decision:true})
  investigation.task = {id:'a', status:'DONE', user_name:name}
  expect(investigation.pending).toBeNull()
})

test('review permissions: authenticated waiting only, independent of role, never legacy', () => {
  const {investigation, identity} = stores()
  const task: Task = {id:'a', status:'WAITING_APPROVAL'}
  expect(investigation.canReview(task)).toBe(true)
  for (const role of ['worker', 'admin'] as const) {
    identity.role = role
    expect(investigation.canReview(task)).toBe(true)
  }
  identity.role = 'engineer'
  expect(investigation.canReview({...task, legacy:true})).toBe(false)
  expect(investigation.canReview({id:'a', status:'DONE'})).toBe(false)
  identity.status = 'anonymous'
  expect(investigation.canReview(task)).toBe(false)
})

test('attribution uses stable subject rather than display name and citations highlight evidence', () => {
  const {investigation, identity, ui} = stores()
  identity.role = 'worker'
  expect(investigation.isOwner({id:'a', status:'DONE', user_name:'renamed', user_id:'account-1'})).toBe(true)
  expect(investigation.isOwner({id:'a', status:'DONE', user_name:'another-worker', user_role:'worker'})).toBe(false)
  ui.openEvidence('DOC#1')
  expect(ui.highlight.id).toBe('DOC#1')
  expect(ui.evidenceOpen).toBe(true)
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

test('chat judgement: buttons and typed text map to /approval without a reviewer field', async () => {
  const {investigation} = stores()
  const waiting = () => {
    investigation.task = {id:'a', status:'WAITING_APPROVAL', user_name:name, report:{}}
    investigation.events = [{seq:1, type:'APPROVAL_REQUIRED', payload:{report:{}}}]
  }
  waiting()
  await investigation.choose('승인')
  waiting()
  await investigation.choose('미승인')
  waiting()
  investigation.draft = 'RF 근거를 다시 확인'
  await investigation.submitQuestion()
  const bodies = calls.filter(item => item[0] === 'approval').map(item => item[2])
  expect(bodies).toEqual([{action:'approve', comment:''}, {action:'revise', comment:''}, {action:'revise', comment:'RF 근거를 다시 확인'}])
  expect(investigation.draft).toBe('')
  expect(calls.some(item => item[0] === 'message')).toBe(false)
})

test('quick reply to a QUESTION is sent as a message and keeps the typed draft', async () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'WAITING_INPUT', user_name:name}
  investigation.events = [{seq:1, type:'QUESTION', payload:{text:'?', options:['건너뛰기']}}]
  investigation.draft = '작성 중'
  await investigation.choose('건너뛰기')
  expect(calls.find(item => item[0] === 'message')).toEqual(['message', 'a', '건너뛰기'])
  expect(investigation.draft).toBe('작성 중')
})

test('TOKEN deltas stream into one bubble and clear on the next saved event', () => {
  const {investigation} = stores()
  let handlers: {onEvent: (event: TaskEvent) => void, onToken: (delta: string, target: string) => void} | undefined
  api.stream = (_id: string, _after: number, h: typeof handlers) => { handlers = h; return () => {} }
  investigation.task = {id:'a', status:'RUNNING', user_name:name}
  investigation.connectStream()
  handlers!.onToken('유사 ', 'summary')
  handlers!.onToken('사례', 'summary')
  expect(investigation.streaming).toEqual({target:'summary', text:'유사 사례'})
  handlers!.onEvent({seq:1, type:'APPROVAL_REQUIRED', payload:{report:{summary:'유사 사례'}}})
  expect(investigation.streaming).toBeNull()
  expect(investigation.task!.status).toBe('WAITING_APPROVAL')
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

test('agent flow follows develop graph events and shows each agent result from stages', () => {
  const {investigation} = stores()
  const states = () => investigation.flow.map(step => step.state)
  investigation.task = {id:'a', status:'RUNNING'}
  expect(states()).toEqual(['active', 'pending', 'pending', 'pending', 'pending', 'pending', 'pending', 'pending', 'pending'])
  investigation.applyEvents([{seq:1, type:'SEARCH_STARTED', payload:{}}])
  expect(states().slice(0, 3)).toEqual(['done', 'active', 'pending'])
  // Physics, sensor, maintenance and recommendation have no events: the specialist run is active together.
  investigation.applyEvents([{seq:2, type:'ANALYSIS_STARTED', payload:{}}])
  expect(states()).toEqual(['done', 'done', 'active', 'active', 'active', 'active', 'active', 'pending', 'pending'])
  investigation.applyEvents([{seq:3, type:'REPORT_STARTED', payload:{}},
    {seq:4, type:'APPROVAL_REQUIRED', payload:{report:{stages:[
      {key:'scope', title:'범위 조사 에이전트', status:'sample_based', agent_mode:'llm'},
      {key:'maintenance', title:'정비 이력 확인 에이전트', status:'unavailable'}]}}}])
  expect(investigation.task!.status).toBe('WAITING_APPROVAL')
  expect(states().at(-1)).toBe('active')
  expect(investigation.flow[1]!.result).toBe('데모 사례 · LLM')
  expect(investigation.flow[5]!.result).toBe('데이터 미연결 · 규칙')
  // Rejection sends the agent back to report writing; approval finishes the flow.
  investigation.applyEvents([{seq:5, type:'REVIEWED', payload:{action:'revise'}}])
  expect(investigation.flow[7]!.state).toBe('active')
  investigation.applyEvents([{seq:6, type:'APPROVAL_REQUIRED', payload:{}}, {seq:7, type:'DONE', payload:{}}])
  expect(states().every(state => state === 'done')).toBe(true)
})

test('agent flow marks where a failed run stopped and keeps clarification at intake', () => {
  const {investigation} = stores()
  investigation.task = {id:'a', status:'RUNNING'}
  investigation.applyEvents([{seq:1, type:'QUESTION', payload:{text:'?'}}])
  expect(investigation.task!.status).toBe('WAITING_INPUT')
  expect(investigation.flow[0]!.state).toBe('active')
  investigation.applyEvents([{seq:2, type:'SEARCH_STARTED', payload:{}}, {seq:3, type:'INCOMPLETE', payload:{reason:'사례 없음'}}])
  expect(investigation.flow.map(step => step.state).slice(0, 3)).toEqual(['done', 'stopped', 'pending'])
})
