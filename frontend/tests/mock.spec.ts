import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { MockError, createMockStore, type Pushed } from '../mock/store'

const engineer = {name:'이엔지니어', role:'engineer'}
let store: ReturnType<typeof createMockStore>

beforeEach(() => {
  vi.useFakeTimers()
  store = createMockStore({delay:10, tokenDelay:1, seed:false})
})
afterEach(() => vi.useRealTimers())

const run = () => vi.advanceTimersByTimeAsync(5_000)
const status = (id: string) => store.detail(engineer, id).status
const types = (id: string) => store.events(engineer, id, 0).map(event => event.type)
const lastPayload = (id: string) => store.events(engineer, id, 0).at(-1)!.payload
const fails = (fn: () => unknown, code: number) =>
  expect(fn).toThrowError(expect.objectContaining({status:code}) as unknown as MockError)

test('full chat flow: clarify, report, reject, revise, approve, record, done', async () => {
  const pushed: Pushed[] = []
  const {taskId} = store.create(engineer, {question:'endpoint가 118초로 지연돼'})
  store.subscribe(engineer, taskId, event => pushed.push(event))
  await run()
  expect(status(taskId)).toBe('WAITING_INPUT')
  expect(lastPayload(taskId)).toMatchObject({missing:['scope'], options:['ETCH-07 CH-B', 'ETCH-09 CH-A']})

  store.message(engineer, taskId, {text:'ETCH-07 CH-B'})
  await run()
  expect(status(taskId)).toBe('WAITING_APPROVAL')
  expect(lastPayload(taskId).options).toEqual(['승인', '미승인'])

  store.approval(engineer, taskId, {action:'revise', comment:''})
  await run()
  expect(lastPayload(taskId).text).toBe('어떤 부분을 수정할까요?')
  store.message(engineer, taskId, {text:'RF 근거 보강'})
  await run()
  expect(status(taskId)).toBe('WAITING_APPROVAL')
  expect(store.detail(engineer, taskId).report!.feedback).toEqual(['RF 근거 보강'])

  store.approval(engineer, taskId, {action:'approve'})
  await run()
  expect(lastPayload(taskId).options).toEqual(['건너뛰기'])
  store.message(engineer, taskId, {text:'10:20, LOT-1'})
  await run()
  const detail = store.detail(engineer, taskId)
  expect(detail.status).toBe('DONE')
  expect(detail.investigation).toMatchObject({event_time:'10:20', lot_id:'LOT-1', approved_by:'이엔지니어'})

  const seqs = store.events(engineer, taskId, 0).map(event => event.seq)
  expect(seqs).toEqual(seqs.map((_, index) => index + 1))
  expect(types(taskId)).not.toContain('TOKEN')
  expect(pushed.some(event => event.type === 'TOKEN')).toBe(true)
  expect(store.events(engineer, taskId, seqs.length - 1).map(event => event.type)).toEqual(['DONE'])
})

test('rejection with a comment rewrites at once without a follow-up question', async () => {
  const {taskId} = store.create(engineer, {question:'ETCH-09 CH-A etch rate 430 저하'})
  await run()
  store.approval(engineer, taskId, {action:'revise', comment:'압력 사례 추가'})
  await run()
  expect(status(taskId)).toBe('WAITING_APPROVAL')
  expect(types(taskId).filter(type => type === 'QUESTION')).toHaveLength(0)
})

test('access and state rules follow docs/api.md', async () => {
  const {taskId} = store.create(engineer, {question:'ETCH-07 endpoint 지연'})
  fails(() => store.create(engineer, {question:'  '}), 422)
  fails(() => store.detail({name:'작업자', role:'worker'}, taskId), 404)
  fails(() => store.approval(engineer, taskId, {action:'approve'}), 409)
  fails(() => store.message(engineer, taskId, {text:'추가'}), 409)
  await run()
  fails(() => store.approval({name:'관리자', role:'admin'}, taskId, {action:'approve'}), 403)
  fails(() => store.approval(engineer, taskId, {action:'maybe'}), 422)
  fails(() => store.sop('NOPE'), 404)
  expect(store.list({name:'작업자', role:'worker'})).toEqual([])
})

test('keywords drive terminal states for UI testing', async () => {
  const failed = store.create(engineer, {question:'ETCH-07 실패 테스트'}).taskId
  const incomplete = store.create(engineer, {question:'ETCH-07 근거 없음'}).taskId
  await run()
  expect(status(failed)).toBe('FAILED')
  expect(status(incomplete)).toBe('INCOMPLETE')
})

test('seed data covers done, waiting judgement and waiting input', () => {
  const seeded = createMockStore({seed:true}).list(engineer).map(task => task.status).sort()
  expect(seeded).toEqual(['DONE', 'WAITING_APPROVAL', 'WAITING_INPUT'])
})
