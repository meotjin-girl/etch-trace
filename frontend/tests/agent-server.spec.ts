import { expect, test, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { createAgentApi } from '@/api/agent-server'
import { readAgentStream } from '@/api/agent-stream'
import { createLiveApi } from '@/api/live-investigations'
import { threadMessages, type ThreadMessage } from '@/api/thread-messages'
import { detail, json, snapshot, sse, summary, values } from './live-fixtures'

const auth = () => ({getToken:vi.fn(async () => 'access-token'), invalidate:vi.fn()})

test('business requests use bearer identity and approve the candidate ID at the displayed revision', async () => {
  // Given a business client and exact backend response contracts.
  const calls: {url: string, init: RequestInit}[] = []
  const session = auth(), signal = new AbortController().signal
  const api = createLiveApi(session, {fetch:async (url, init = {}) => {
    calls.push({url:String(url), init})
    return json(init.method === 'POST' ? snapshot : String(url).endsWith('/investigations') ? [summary] : detail)
  }})
  // When reading and selecting a candidate.
  expect(await api.list(signal)).toEqual([summary])
  expect(await api.detail('a/b', signal)).toEqual(detail)
  expect(await api.approve('a/b', {candidate_id:snapshot.candidate.id, expected_revision:3, comment:''}, signal)).toEqual(snapshot)
  // Then only backend IDs and concurrency revision, never position or reviewer, are submitted.
  expect(calls.map(call => call.url)).toEqual(['/api/investigations', '/api/investigations/a%2Fb', '/api/investigations/a%2Fb/approval'])
  expect(JSON.parse(String(calls[2]?.init.body))).toEqual({candidate_id:snapshot.candidate.id, expected_revision:3, comment:''})
  for (const call of calls) {
    expect(new Headers(call.init.headers).get('Authorization')).toBe('Bearer access-token')
    expect(new Headers(call.init.headers).has('X-Internal-Key')).toBe(false)
    expect(call.init.signal).toBe(signal)
  }
})

test('business boundary rejects malformed candidates and invalidates denied sessions', async () => {
  // Given invalid backend data and an expired token.
  const session = auth()
  const malformed = createLiveApi(session, {fetch:async () => json({...detail, candidates:[{...snapshot.candidate, checks:7}]})})
  const denied = createLiveApi(session, {fetch:async () => json({}, 401)})
  // When reading each response, then invalid data never reaches rendering.
  await expect(malformed.detail(detail.id)).rejects.toBeInstanceOf(ApiError)
  await expect(denied.list()).rejects.toMatchObject({status:401})
  expect(session.invalidate).toHaveBeenCalledOnce()
})

test('thread messages expose user and final assistant text without tool-call intermediates', () => {
  // Given LangChain and role-format messages, including a tool call that has prose.
  const state = {messages:[
    {type:'human', id:'u1', content:'question'},
    {type:'ai', content:'Searching secret tool', tool_calls:[{name:'search'}]},
    {type:'tool', content:'private tool result'},
    {role:'assistant', content:[{type:'tool_use', id:'tool-1'}, {type:'text', text:'hidden'}]},
    {role:'assistant', content:'hidden extra', additional_kwargs:{tool_calls:[{id:'tool-2'}]}},
    {type:'system', content:'instructions'},
    {type:'ai', id:'a1', content:[{type:'thinking', thinking:'hidden'}, {type:'text', text:'final answer'}]},
  ]}
  // When projecting the history, then only the visible conversation survives.
  expect(threadMessages(state)).toEqual([
    {id:'u1', role:'user', text:'question'}, {id:'a1', role:'assistant', text:'final answer'},
  ])
})

test('values SSE decodes byte-split Korean CRLF and replaces snapshots without duplicate messages', async () => {
  // Given split bytes, comments, metadata, multiline values and an incomplete tail.
  const input = ': heartbeat\r\nevent: metadata\r\ndata: {"run_id":"r"}\r\n\r\n' +
    'event: values\r\ndata: {"messages":[\r\ndata: {"type":"ai","id":"a","content":"장비"}]}\r\n\r\n' +
    values([{type:'ai', id:'a', content:'장비 확인'}]) + 'event: values\ndata: {"messages":[]}'
  const body = new ReadableStream<Uint8Array>({start(controller) {
    for (const byte of new TextEncoder().encode(input)) controller.enqueue(Uint8Array.of(byte))
    controller.close()
  }})
  const received: ThreadMessage[][] = []
  // When reading the stream.
  await readAgentStream(body, {signal:new AbortController().signal, onMessages:items => received.push(items)})
  // Then snapshots have stable IDs and incomplete EOF does not erase the last one.
  expect(received).toEqual([
    [{id:'a', role:'assistant', text:'장비'}], [{id:'a', role:'assistant', text:'장비 확인'}],
  ])
})

test('Agent Server reads values.messages and sends the frozen graph input and continuation policy', async () => {
  // Given an authenticated Agent Server.
  const calls: {url: string, init: RequestInit}[] = []
  const api = createAgentApi(auth(), {fetch:async (url, init = {}) => {
    calls.push({url:String(url), init})
    return String(url).endsWith('/state') ? json({values:{messages:[{type:'human', content:'prior'}]}})
      : sse(values([{type:'ai', content:'reply'}]) + 'event: end\ndata: {}\n\n')
  }})
  const onMessages = vi.fn(), onAccepted = vi.fn(), signal = new AbortController().signal
  // When loading, sending and joining.
  expect(await api.state('a/b', signal)).toEqual([{id:'message-0', role:'user', text:'prior'}])
  await api.send('a/b', 'follow-up', {signal, onMessages, onAccepted})
  await api.join('a/b', 'run/1', {signal, onMessages})
  // Then the exact thread and run are used, never a new thread.
  expect(JSON.parse(String(calls[1]?.init.body))).toEqual({
    assistant_id:'trace', input:{request:{role:'user', content:'follow-up'}},
    stream_mode:['values'], multitask_strategy:'reject', on_disconnect:'continue',
  })
  expect(calls[2]?.url).toBe('/agent/threads/a%2Fb/runs/run%2F1/stream?stream_mode=values&cancel_on_disconnect=false')
  expect(calls[2]?.init.method).toBeUndefined()
  expect(onAccepted).toHaveBeenCalledOnce()
  expect(onMessages).toHaveBeenCalledTimes(2)
  for (const call of calls) expect(new Headers(call.init.headers).get('Authorization')).toBe('Bearer access-token')
})

test('agent stream reports error events and rejects a non-stream response', async () => {
  // Given a failed run and a proxy returning HTML.
  const options = {signal:new AbortController().signal, onMessages:vi.fn()}
  const failed = createAgentApi(auth(), {fetch:async () => sse('event: error\ndata: {"message":"failed"}\n\n')})
  const html = createAgentApi(auth(), {fetch:async () => new Response('<html>')})
  // When streaming, then neither failure is treated as completion.
  await expect(failed.send('t', 'question', options)).rejects.toBeInstanceOf(ApiError)
  await expect(html.send('t', 'question', options)).rejects.toBeInstanceOf(ApiError)
  expect(options.onMessages).not.toHaveBeenCalled()
})

test('leaving a thread cancels the pending stream reader without delivering late values', async () => {
  // Given a pending read with exact start/cancel signals.
  const started = Promise.withResolvers<void>(), cancelled = Promise.withResolvers<void>()
  const body = new ReadableStream<Uint8Array>({pull() { started.resolve() }, cancel() { cancelled.resolve() }})
  const controller = new AbortController(), onMessages = vi.fn()
  const reading = readAgentStream(body, {signal:controller.signal, onMessages})
  await started.promise
  // When leaving the page.
  controller.abort()
  await cancelled.promise
  await reading
  // Then the read is cancelled and no stale conversation is delivered.
  expect(onMessages).not.toHaveBeenCalled()
})
