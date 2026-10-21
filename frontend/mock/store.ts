// In-memory mock of the backend + agent, following docs/api.md and the
// conversational proposal in docs/frontend.md (QUESTION.options, TOKEN,
// chat approval with follow-up questions). Dev/test only.
import { randomUUID } from 'node:crypto'
import type { Report, Review, Task, TaskEvent } from '../src/api/types'
import { buildReport, sopDocuments } from './fixtures'

export interface MockIdentity { name: string, role: string }
export type MockEvent = TaskEvent & { task_id: string, event_id: string }
export type Pushed = MockEvent | { type: 'TOKEN', payload: { delta: string, target: string } }

export class MockError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

// What the agent is waiting for while the task is WAITING_INPUT.
type Phase = 'scope' | 'symptom' | 'revise' | 'record' | null
interface MockTask extends Task {
  events: MockEvent[]
  reviews: Review[]
  investigation: Record<string, unknown> | null
  phase: Phase
  feedback: string[]
}

const terminal = new Set(['DONE', 'INCOMPLETE', 'FAILED'])
const symptom = /endpoint|etch rate|rf|pressure|압력|지연|저하|상승|불안정/i
const now = () => new Date().toISOString()

export function createMockStore({delay = 700, tokenDelay = 35, seed = true} = {}) {
  const tasks = new Map<string, MockTask>()
  const listeners = new Map<string, Set<(event: Pushed) => void>>()
  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

  function notify(task: MockTask, event: Pushed) {
    listeners.get(task.id)?.forEach(listener => listener(event))
  }
  function emit(task: MockTask, type: string, payload: Record<string, unknown> = {}, at = now()) {
    const event: MockEvent = {task_id:task.id, event_id:randomUUID(), seq:task.events.length + 1, type, payload, created_at:at}
    task.events.push(event)
    task.updated_at = at
    notify(task, event)
  }
  async function streamText(task: MockTask, target: string, text: string) {
    for (let i = 0; i < text.length; i += 3) {
      notify(task, {type:'TOKEN', payload:{delta:text.slice(i, i + 3), target}})
      await sleep(tokenDelay)
    }
  }
  function say(task: MockTask, text: string, at?: string) {
    task.messages!.push({role:'assistant', text, created_at:at ?? now()})
  }

  // --- agent behaviour -------------------------------------------------
  async function ask(task: MockTask, phase: Phase, text: string, extra: Record<string, unknown> = {}) {
    await streamText(task, 'message', text)
    task.phase = phase
    task.status = 'WAITING_INPUT'
    say(task, text)
    emit(task, 'QUESTION', {text, ...extra})
  }
  async function writeReport(task: MockTask) {
    for (const type of ['SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED']) {
      emit(task, type)
      await sleep(delay)
    }
    const report: Report = buildReport(userText(task), task.feedback)
    await streamText(task, 'summary', String(report.summary))
    task.report = report
    task.status = 'WAITING_APPROVAL'
    emit(task, 'APPROVAL_REQUIRED', {report, text:'보고서를 판별해 주세요', options:['승인', '미승인']})
  }
  async function intake(task: MockTask) {
    const text = userText(task)
    if (text.includes('실패')) return finish(task, 'FAILED', {error:'목업: 에이전트 실행 중 오류가 발생했습니다.'})
    if (text.includes('근거 없음')) return finish(task, 'INCOMPLETE', {reason:'목업: 유사 사례 근거가 부족합니다.'})
    if (!/ETCH-\d+/.test(text)) {
      return ask(task, 'scope', '어느 장비와 챔버에서 발생했나요?', {missing:['scope'], options:['ETCH-07 CH-B', 'ETCH-09 CH-A']})
    }
    if (!symptom.test(text)) {
      return ask(task, 'symptom', '관찰된 현상과 수치를 알려주세요.', {missing:['symptom'], options:['Endpoint 118초 지연', 'Etch rate 430으로 저하']})
    }
    return writeReport(task)
  }
  function finish(task: MockTask, type: string, payload: Record<string, unknown>) {
    task.status = type
    task.phase = null
    emit(task, type, payload)
  }
  async function resume(task: MockTask, run: () => Promise<void> | void) {
    task.status = 'RUNNING'
    emit(task, 'RUNNING')
    await sleep(delay)
    await run()
  }
  const userText = (task: MockTask) => (task.messages || []).filter(item => item.role === 'user').map(item => item.text).join(' ')

  // --- access ----------------------------------------------------------
  function visible(identity: MockIdentity, id: string) {
    const task = tasks.get(id)
    if (!task) throw new MockError(404, '작업을 찾을 수 없습니다.')
    return task
  }
  function requireText(value: unknown, field: string) {
    if (typeof value !== 'string' || !value.trim() || value.length > 10000) throw new MockError(422, `${field}는 1~10,000자 문자열이어야 합니다.`)
    return value.trim()
  }
  const summary = ({events, messages, reviews, investigation, phase, feedback, ...task}: MockTask) => task
  const detail = ({phase, feedback, ...task}: MockTask) => structuredClone(task)

  // --- public API (mirrors /api/ai/tasks and /api/sops) -----------------
  const api = {
    list(identity: MockIdentity) {
      return [...tasks.values()]
        .sort((a, b) => b.created_at!.localeCompare(a.created_at!))
        .map(summary)
    },
    create(identity: MockIdentity, body: {question?: unknown}) {
      const question = requireText(body?.question, 'question')
      const at = now()
      const task: MockTask = {
        id:randomUUID(), user_name:identity.name, user_role:identity.role, question,
        status:'QUEUED', report:null, created_at:at, updated_at:at,
        messages:[{role:'user', text:question, created_at:at}], events:[], reviews:[],
        investigation:null, phase:null, feedback:[]
      }
      tasks.set(task.id, task)
      emit(task, 'QUEUED', {by:identity.name})
      void (async () => { await sleep(delay); await resume(task, () => intake(task)) })()
      return {taskId:task.id}
    },
    detail(identity: MockIdentity, id: string) { return detail(visible(identity, id)) },
    events(identity: MockIdentity, id: string, after: number) {
      return visible(identity, id).events.filter(event => event.seq > after).map(event => structuredClone(event))
    },
    message(identity: MockIdentity, id: string, body: {text?: unknown}) {
      const task = visible(identity, id)
      if (task.status !== 'WAITING_INPUT') throw new MockError(409, '추가 정보를 기다리는 상태가 아닙니다.')
      const text = requireText(body?.text, 'text')
      task.messages!.push({role:'user', text, created_at:now()})
      emit(task, 'MESSAGE', {text, by:identity.name})
      const phase = task.phase
      task.phase = null
      void resume(task, () => {
        if (phase === 'revise') { task.feedback.push(text); return writeReport(task) }
        if (phase === 'record') return record(task, text)
        return intake(task)
      })
      return {taskId:task.id}
    },
    approval(identity: MockIdentity, id: string, body: {action?: unknown, comment?: unknown}) {
      const task = visible(identity, id)
      if (task.status !== 'WAITING_APPROVAL') throw new MockError(409, '판별 대기 상태가 아닙니다.')
      const action = body?.action
      if (action !== 'approve' && action !== 'revise') throw new MockError(422, 'action은 approve 또는 revise입니다.')
      const comment = typeof body.comment === 'string' ? body.comment.trim() : ''
      const at = now()
      task.reviews.push({action, comment, by:identity.name, role:identity.role, report:task.report, created_at:at})
      emit(task, 'REVIEWED', {action, comment, by:identity.name, role:identity.role})
      void resume(task, () => {
        if (action === 'approve') return ask(task, 'record', '기록할 발생 시각과 Lot ID를 알려주세요.', {options:['건너뛰기']})
        if (comment) { task.feedback.push(comment); return writeReport(task) }
        return ask(task, 'revise', '어떤 부분을 수정할까요?')
      })
      return {taskId:task.id}
    },
    subscribe(identity: MockIdentity, id: string, listener: (event: Pushed) => void) {
      const task = visible(identity, id)
      if (!listeners.has(task.id)) listeners.set(task.id, new Set())
      listeners.get(task.id)!.add(listener)
      return () => listeners.get(task.id)?.delete(listener)
    },
    isTerminal: (identity: MockIdentity, id: string) => terminal.has(visible(identity, id).status),
    sops: () => sopDocuments.map(({markdown, ...item}) => ({...item, demo:true})),
    sop(id: string) {
      const item = sopDocuments.find(doc => doc.id === id)
      if (!item) throw new MockError(404, '문서를 찾을 수 없습니다.')
      return {...item, demo:true}
    },
  }

  function record(task: MockTask, text: string) {
    const approval = [...task.reviews].reverse().find(item => item.action === 'approve')
    const skipped = text === '건너뛰기'
    task.investigation = {
      approved_by:approval?.by, approved_role:approval?.role, approved_at:approval?.created_at,
      event_time:skipped ? null : text.match(/\d{1,2}:\d{2}/)?.[0] ?? null,
      lot_id:skipped ? null : text.match(/LOT[-\w]*/i)?.[0] ?? null,
      report:task.report
    }
    say(task, '조사 기록을 저장했습니다.')
    finish(task, 'DONE', {report:task.report, approved:true, by:approval?.by})
  }

  // Seed data: written instantly with past timestamps so every screen has content.
  function seedTask(question: string, minutesAgo: number, steps: (task: MockTask, at: () => string) => void) {
    let clock = Date.now() - minutesAgo * 60_000
    const at = () => new Date(clock += 2000).toISOString()
    const created = at()
    const task: MockTask = {
      id:randomUUID(), user_name:'이엔지니어', user_role:'engineer', question, status:'QUEUED', report:null,
      created_at:created, updated_at:created, messages:[{role:'user', text:question, created_at:created}],
      events:[], reviews:[], investigation:null, phase:null, feedback:[]
    }
    tasks.set(task.id, task)
    emit(task, 'QUEUED', {by:task.user_name}, created)
    emit(task, 'RUNNING', {}, at())
    steps(task, at)
  }
  function seedReport(task: MockTask, at: () => string) {
    for (const type of ['SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED']) emit(task, type, {}, at())
    task.report = buildReport(userText(task), task.feedback)
    task.status = 'WAITING_APPROVAL'
    emit(task, 'APPROVAL_REQUIRED', {report:task.report, text:'보고서를 판별해 주세요', options:['승인', '미승인']}, at())
  }
  if (seed) {
    seedTask('ETCH-07 CH-B OX-120 endpoint 118초 지연, RF reflected 29W', 180, (task, at) => {
      seedReport(task, at)
      const reviewedAt = at()
      task.reviews.push({action:'approve', comment:'', by:'이엔지니어', role:'engineer', report:task.report, created_at:reviewedAt})
      emit(task, 'REVIEWED', {action:'approve', comment:'', by:'이엔지니어', role:'engineer'}, reviewedAt)
      emit(task, 'RUNNING', {}, at())
      const question = '기록할 발생 시각과 Lot ID를 알려주세요.'
      say(task, question, at())
      emit(task, 'QUESTION', {text:question, options:['건너뛰기']}, at())
      task.messages!.push({role:'user', text:'10:20, LOT-261020-03', created_at:at()})
      emit(task, 'MESSAGE', {text:'10:20, LOT-261020-03', by:'이엔지니어'}, at())
      emit(task, 'RUNNING', {}, at())
      task.investigation = {approved_by:'이엔지니어', approved_role:'engineer', approved_at:reviewedAt, event_time:'10:20', lot_id:'LOT-261020-03', report:task.report}
      say(task, '조사 기록을 저장했습니다.', at())
      task.status = 'DONE'
      emit(task, 'DONE', {report:task.report, approved:true, by:'이엔지니어'}, at())
    })
    seedTask('ETCH-09 CH-A OX-120 etch rate 430으로 저하, pressure 불안정', 60, seedReport)
    seedTask('챔버에서 endpoint가 계속 늦어져', 10, (task, at) => {
      const question = '어느 장비와 챔버에서 발생했나요?'
      say(task, question, at())
      task.status = 'WAITING_INPUT'
      task.phase = 'scope'
      emit(task, 'QUESTION', {text:question, missing:['scope'], options:['ETCH-07 CH-B', 'ETCH-09 CH-A']}, at())
    })
  }

  return api
}

export type MockStore = ReturnType<typeof createMockStore>
