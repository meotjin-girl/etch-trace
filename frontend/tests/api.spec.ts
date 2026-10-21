import { describe, expect, test } from 'vitest'
import { ApiError, createApi, mergeEvents, streamUrl, type EventSourceLike } from '@/api/client'
import type { Identity, TaskEvent } from '@/api/types'

const identity: Identity = {name:'이엔지니어', role:'engineer'}
const fail = () => { throw new Error('unexpected call') }

test('HTTP contract: encoded actor, routes, JSON bodies and abort signals', async () => {
  const calls: (RequestInit & {url: string})[] = []
  const controller = new AbortController()
  const api = createApi(identity, {fetch:(async (url: string, options: RequestInit) => {
    calls.push({url, ...options})
    return new Response('{"taskId":"t/1"}', {status:202})
  }) as typeof fetch})
  await api.create('질문', controller.signal)
  await api.message('t/1', '추가 정보', controller.signal)
  await api.approval('t/1', {action:'revise', comment:'확인'}, controller.signal)
  await api.list(controller.signal)
  await api.detail('t/1', controller.signal)
  await api.events('t/1', 7, controller.signal)
  const headers = calls[0]!.headers as Record<string, string>
  expect(headers['X-User-Name']).toBe(encodeURIComponent(identity.name))
  expect(headers['X-User-Role']).toBe('engineer')
  expect(JSON.parse(calls[0]!.body as string)).toEqual({question:'질문'})
  expect(JSON.parse(calls[1]!.body as string)).toEqual({text:'추가 정보'})
  expect(calls[2]!.url).toBe('/api/ai/tasks/t%2F1/approval')
  expect(calls[3]!.method).toBe('GET')
  expect(calls[4]!.url).toBe('/api/ai/tasks/t%2F1')
  expect(calls[5]!.url).toBe('/api/ai/tasks/t%2F1/events?after=7')
  expect(calls.every(call => call.signal === controller.signal)).toBe(true)
})

test('errors retain server denial and distinguish cancellation/network/bad JSON', async () => {
  const using = (fetch: () => Promise<Response>) => createApi(identity, {fetch: fetch as typeof globalThis.fetch})
  await expect(using(async () => new Response('{"detail":"engineer only"}', {status:403})).list())
    .rejects.toSatisfy((error: unknown) => error instanceof ApiError && error.status === 403 && error.message === 'engineer only')
  await expect(using(async () => { throw new TypeError('offline') }).list()).rejects.toBeInstanceOf(ApiError)
  await expect(using(async () => new Response('<html>')).list()).rejects.toBeInstanceOf(ApiError)
  const abort = new DOMException('cancelled', 'AbortError')
  await expect(using(async () => { throw abort }).list()).rejects.toBe(abort)
})

class FakeSource implements EventSourceLike {
  static instances: FakeSource[] = []
  listeners: Record<string, (event: MessageEvent) => void> = {}
  onmessage: EventSourceLike['onmessage'] = null
  onerror: EventSourceLike['onerror'] = null
  closed = false
  constructor(public url: string) { FakeSource.instances.push(this) }
  addEventListener(type: string, fn: (event: MessageEvent) => void) { this.listeners[type] = fn }
  close() { this.closed = true }
  emit(type: string, data: unknown, id = '') {
    this.listeners[type]!({type, data:JSON.stringify(data), lastEventId:id} as MessageEvent)
  }
}
const latest = () => FakeSource.instances.at(-1)!

describe('SSE', () => {
  test('identity, payload variants, close on abort and explicit reconnect cursor', () => {
    const api = createApi(identity, {EventSource:FakeSource})
    const controller = new AbortController()
    const events: TaskEvent[] = []
    api.stream('a', 4, {signal:controller.signal, onEvent:event => events.push(event), onError:fail})
    const source = latest()
    const url = new URL(source.url, 'https://example.test')
    expect(url.searchParams.get('user_name')).toBe(identity.name)
    expect(url.searchParams.get('user_role')).toBe('engineer')
    expect(url.searchParams.get('after')).toBe('4')
    source.emit('QUESTION', {text:'장비?', missing:['tool']}, '5')
    source.emit('DONE', {seq:6, type:'DONE', payload:{report:{demo:true}}})
    expect(events[0]!.seq).toBe(5)
    expect(events[0]!.payload.text).toBe('장비?')
    expect(events[1]!.payload.report.demo).toBe(true)
    controller.abort()
    expect(source.closed).toBe(true)
    source.emit('DONE', {seq:7})
    expect(events).toHaveLength(2)
    expect(streamUrl('a', identity, 6)).toMatch(/after=6/)
  })

  test('malformed events and disconnect become recoverable errors', () => {
    const errors: ApiError[] = []
    const api = createApi(identity, {EventSource:FakeSource})
    api.stream('a', 0, {onEvent:fail, onError:error => errors.push(error)})
    let source = latest()
    source.emit('DONE', {})
    expect(source.closed).toBe(true)
    api.stream('a', 0, {onEvent:fail, onError:error => errors.push(error)})
    source = latest()
    source.onerror!(new Event('error'))
    expect(source.closed).toBe(true)
    expect(errors).toHaveLength(2)
  })
})

test('event replay merges and deduplicates numeric sequence', () => {
  const events = mergeEvents([{seq:2, type:'RUNNING', payload:{}}], [
    {seq:1, type:'QUEUED', payload:{}}, {seq:'2' as unknown as number, type:'RUNNING', payload:{}},
    {seq:3, type:'QUESTION', payload:{}}, {seq:0, type:'', payload:{}}
  ])
  expect(events.map(event => event.seq)).toEqual([1, 2, 3])
})

test('SOP routes carry the same identity headers', async () => {
  const calls: {url: string, headers: Record<string, string>}[] = []
  const api = createApi(identity, {fetch:(async (url: string, options: RequestInit) => {
    calls.push({url, headers:options.headers as Record<string, string>})
    return new Response('[]')
  }) as typeof fetch})
  await api.sops()
  await api.sop('SOP/1')
  expect(calls.map(call => call.url)).toEqual(['/api/sops', '/api/sops/SOP%2F1'])
  expect(calls[1]!.headers['X-User-Role']).toBe('engineer')
})

test('TOKEN deltas bypass sequence checks and never become saved events', () => {
  const api = createApi(identity, {EventSource:FakeSource})
  const tokens: string[] = []
  const events: TaskEvent[] = []
  api.stream('a', 0, {onEvent:event => events.push(event), onError:fail, onToken:(delta, target) => tokens.push(`${target}:${delta}`)})
  const source = latest()
  source.emit('TOKEN', {delta:'유사', target:'summary'})
  source.emit('TOKEN', {delta:' 사례'})
  expect(tokens).toEqual(['summary:유사', 'message: 사례'])
  expect(events).toHaveLength(0)
  expect(source.closed).toBe(false)
})
