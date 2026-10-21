import { expect, test, vi } from 'vitest'
import { ApiError, createApi, mergeEvents, readEventStream, streamUrl } from '@/api/client'
import type { TaskEvent } from '@/api/types'

const auth = () => ({getToken: vi.fn(async () => 'access-token'), invalidate: vi.fn()})
const bytes = (chunks: readonly string[]) => new ReadableStream<Uint8Array>({
  start(controller) {
    chunks.forEach(chunk => controller.enqueue(new TextEncoder().encode(chunk)))
    controller.close()
  },
})
const sse = (text: string) => new Response(bytes([text]), {headers: {'Content-Type': 'text/event-stream'}})

test('REST uses bearer identity on task and SOP routes and preserves bodies and abort', async () => {
  const session = auth()
  const calls: {url: string, init: RequestInit}[] = []
  const api = createApi(session, {fetch: async (input, init = {}) => {
    calls.push({url: String(input), init})
    return new Response('{"taskId":"t/1"}', {status:202})
  }})
  const controller = new AbortController()
  await api.create('질문', controller.signal)
  await api.message('t/1', '추가 정보', controller.signal)
  await api.approval('t/1', {action:'revise', comment:'확인'}, controller.signal)
  await api.list(controller.signal)
  await api.detail('t/1', controller.signal)
  await api.events('t/1', 7, controller.signal)
  await api.sops(controller.signal)
  await api.sop('SOP/1', controller.signal)
  expect(calls.map(call => call.url)).toEqual([
    '/api/ai/tasks', '/api/ai/tasks/t%2F1/messages', '/api/ai/tasks/t%2F1/approval',
    '/api/ai/tasks', '/api/ai/tasks/t%2F1', '/api/ai/tasks/t%2F1/events?after=7',
    '/api/sops', '/api/sops/SOP%2F1',
  ])
  for (const call of calls) {
    const headers = new Headers(call.init.headers)
    expect(headers.get('Authorization')).toBe('Bearer access-token')
    expect(headers.has('X-User-Name')).toBe(false)
    expect(headers.has('X-User-Role')).toBe(false)
    expect(call.init.signal).toBe(controller.signal)
  }
  expect(calls[0]?.init.body).toBe(JSON.stringify({question:'질문'}))
  expect(calls[1]?.init.body).toBe(JSON.stringify({text:'추가 정보'}))
  expect(session.getToken).toHaveBeenCalledTimes(8)
})

test('REST distinguishes denial, cancellation, network and malformed JSON', async () => {
  const session = auth()
  const using = (fetch: typeof globalThis.fetch) => createApi(session, {fetch})
  await expect(using(async () => new Response('{"detail":"denied"}', {status:401})).list())
    .rejects.toMatchObject({status:401})
  expect(session.invalidate).toHaveBeenCalledOnce()
  await expect(using(async () => { throw new TypeError('offline') }).list()).rejects.toBeInstanceOf(ApiError)
  await expect(using(async () => new Response('<html>')).list()).rejects.toBeInstanceOf(ApiError)
  const abort = new DOMException('cancelled', 'AbortError')
  await expect(using(async () => { throw abort }).list()).rejects.toBe(abort)
})

test('an abort during token renewal prevents any REST fetch', async () => {
  const session = auth()
  const controller = new AbortController()
  session.getToken.mockImplementation(async () => { controller.abort(); return 'new' })
  const fetcher = vi.fn<typeof fetch>()
  await expect(createApi(session, {fetch:fetcher}).list(controller.signal)).rejects.toMatchObject({name:'AbortError'})
  expect(fetcher).not.toHaveBeenCalled()
})

test('SSE handles split CRLF, multiline data, comments and unsaved TOKEN events', async () => {
  const events: TaskEvent[] = []
  const tokens: string[] = []
  await readEventStream(bytes([
    ': heartbeat\r', '\nid: 5\revent: QUESTION\r\ndata: {"text":\r',
    '\ndata: "장비?"}\r\n\r', '\nevent: TOKEN\ndata: {"delta":"유사", "target":"summary"}\n\n',
    'id: 6\nevent: DONE\ndata: {"seq":6,"type":"DONE","payload":{"report":{"demo":true}}}\n\n',
  ]), {onEvent:event => events.push(event), onToken:(delta, target) => tokens.push(target + ':' + delta)})
  expect(events.map(event => event.seq)).toEqual([5, 6])
  expect(events[0]?.payload.text).toBe('장비?')
  expect(events[1]?.payload.report.demo).toBe(true)
  expect(tokens).toEqual(['summary:유사'])
})

test('malformed unsaved TOKEN data does not discard the next saved event', async () => {
  const events: TaskEvent[] = []
  await readEventStream(bytes([
    'event: TOKEN\ndata: malformed\n\nevent: TOKEN\ndata: null\n\n',
    'id: 1\nevent: DONE\ndata: {}\n\n',
  ]), {onEvent:event => events.push(event)})
  expect(events.map(event => event.type)).toEqual(['DONE'])
})

test('SSE decodes multibyte UTF-8 split across network chunks and discards incomplete EOF', async () => {
  const encoded = new TextEncoder().encode('id: 1\nevent: QUESTION\ndata: {"text":"장비"}\n\nid: 2\ndata: {"text":"partial"}')
  const events: TaskEvent[] = []
  const body = new ReadableStream<Uint8Array>({start(controller) {
    for (const byte of encoded) controller.enqueue(Uint8Array.of(byte))
    controller.close()
  }})
  await readEventStream(body, {onEvent:event => events.push(event)})
  expect(events).toHaveLength(1)
  expect(events[0]?.payload.text).toBe('장비')
})

test('SSE reconnects with renewed bearer and latest seq without duplicates', async () => {
  const session = auth()
  session.getToken.mockResolvedValueOnce('old').mockResolvedValue('new')
  const events: TaskEvent[] = []
  const calls: {url:string, token:string | null}[] = []
  const complete = Promise.withResolvers<void>()
  const api = createApi(session, {fetch: async (input, init) => {
    calls.push({url:String(input), token:new Headers(init?.headers).get('Authorization')})
    return sse(calls.length === 1
      ? 'id: 5\nevent: QUESTION\ndata: {"text":"장비?"}\n\n'
      : 'id: 5\nevent: QUESTION\ndata: {"text":"장비?"}\n\nid: 6\nevent: DONE\ndata: {}\n\n')
  }})
  const close = api.stream('a', 4, {onEvent:event => {
    events.push(event)
    if (event.type === 'DONE') complete.resolve()
  }, onError:complete.reject})
  try { await complete.promise } finally { close() }
  expect(events.map(event => event.seq)).toEqual([5, 6])
  expect(calls).toEqual([
    {url:'/api/ai/tasks/a/stream?after=4', token:'Bearer old'},
    {url:'/api/ai/tasks/a/stream?after=5', token:'Bearer new'},
  ])
  expect(streamUrl('a')).not.toMatch(/user_name|user_role|token/)
})

test.each([
  ['invalid event', () => sse('event: QUESTION\ndata: {}\n\n'), 0],
  ['early EOF', () => sse(': heartbeat\n\n'), 0],
  ['denial', () => new Response('{}', {status:401}), 401],
  ['wrong media type', () => new Response('{}'), 0],
] as const)('SSE reports %s once without an automatic retry', async (_name, response, status) => {
  const session = auth()
  const fetcher = vi.fn(async () => response())
  const failed = Promise.withResolvers<ApiError>()
  const receive = vi.fn()
  const close = createApi(session, {fetch:fetcher}).stream('a', 0, {onEvent:receive, onError:failed.resolve})
  try {
    const error = await failed.promise
    expect(error.status).toBe(status)
    expect(fetcher).toHaveBeenCalledOnce()
    expect(receive).not.toHaveBeenCalled()
    expect(session.invalidate).toHaveBeenCalledTimes(status === 401 ? 1 : 0)
  } finally { close() }
})

test('closing a pending SSE read cancels it and suppresses late data', async () => {
  const started = Promise.withResolvers<void>()
  const cancelled = Promise.withResolvers<void>()
  const onEvent = vi.fn(), onError = vi.fn()
  const body = new ReadableStream<Uint8Array>({
    pull() { started.resolve() }, cancel() { cancelled.resolve() },
  })
  const controller = new AbortController()
  const close = createApi(auth(), {fetch:async () => new Response(body, {
    headers:{'Content-Type':'text/event-stream'},
  })}).stream('a', 0, {signal:controller.signal, onEvent, onError})
  await started.promise
  controller.abort()
  await cancelled.promise
  close()
  expect(onEvent).not.toHaveBeenCalled()
  expect(onError).not.toHaveBeenCalled()
})

test('event replay merges and deduplicates numeric sequence', () => {
  const events = mergeEvents([{seq:2, type:'RUNNING', payload:{}}], [
    {seq:1, type:'QUEUED', payload:{}}, {seq:2, type:'RUNNING', payload:{}},
    {seq:3, type:'QUESTION', payload:{}}, {seq:0, type:'', payload:{}},
  ])
  expect(events.map(event => event.seq)).toEqual([1, 2, 3])
})
