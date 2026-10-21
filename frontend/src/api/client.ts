import type { SessionAuth } from '@/auth'
import type { ApprovalBody, Sop, SopSummary, Task, TaskEvent } from './types'

export const EVENT_TYPES = [
  'QUEUED', 'RUNNING', 'SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED',
  'MESSAGE', 'QUESTION', 'APPROVAL_REQUIRED', 'DONE', 'INCOMPLETE', 'FAILED', 'REVIEWED'
] as const

export class ApiError extends Error {
  status: number
  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface Transport {
  fetch?: typeof fetch
}

interface StreamHandlers {
  signal?: AbortSignal
  onEvent: (event: TaskEvent) => void
  onError: (error: ApiError) => void
  // Proposed TOKEN events: unsaved text deltas without a sequence.
  onToken?: (delta: string, target: string) => void
}

export function streamUrl(id: string, after = 0) {
  const query = new URLSearchParams({after: String(after)})
  return `/api/ai/tasks/${encodeURIComponent(id)}/stream?${query}`
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

// Each connection owns its UTF-8 decoder and SSE fields, including split CRLF.
export async function readEventStream(
  body: ReadableStream<Uint8Array>, {signal, onEvent, onToken}: Omit<StreamHandlers, 'onError'>,
) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let line = '', type = '', lastId = '', skipLF = false
  let data: string[] = []
  function dispatch() {
    if (!data.length) { type = ''; return }
    let value: unknown
    try { value = JSON.parse(data.join('\n')) }
    catch (error) {
      if (type !== 'TOKEN' || !(error instanceof SyntaxError)) throw error
      data = []
      type = ''
      return
    }
    if (type === 'TOKEN') {
      if (record(value) && typeof value.delta === 'string') onToken?.(value.delta, String(value.target || 'message'))
    } else {
      if (!record(value)) throw new ApiError('진행 이벤트 형식이 올바르지 않습니다.')
      const seq = Number(value.seq ?? lastId)
      if (!Number.isSafeInteger(seq) || seq < 1) throw new ApiError('진행 이벤트 순서가 올바르지 않습니다.')
      onEvent({
        seq, type: typeof value.type === 'string' ? value.type : type || 'message',
        payload: record(value.payload) ? value.payload : value,
        created_at: typeof value.created_at === 'string' ? value.created_at : undefined,
      })
    }
    data = []
    type = ''
  }
  function consumeLine() {
    if (!line) dispatch()
    else if (!line.startsWith(':')) {
      const colon = line.indexOf(':')
      const field = colon < 0 ? line : line.slice(0, colon)
      let value = colon < 0 ? '' : line.slice(colon + 1)
      if (value.startsWith(' ')) value = value.slice(1)
      if (field === 'data') data.push(value)
      if (field === 'event') type = value
      if (field === 'id' && !value.includes('\0')) lastId = value
    }
    line = ''
  }
  function consume(chunk: string) {
    for (const char of chunk) {
      if (signal?.aborted) return
      if (skipLF) {
        skipLF = false
        if (char === '\n') continue
      }
      if (char === '\r' || char === '\n') {
        consumeLine()
        skipLF = char === '\r'
      } else line += char
    }
  }
  const abort = () => { void reader.cancel() }
  signal?.addEventListener('abort', abort, {once: true})
  try {
    while (!signal?.aborted) {
      const {value, done} = await reader.read()
      if (signal?.aborted) return
      if (done) {
        consume(decoder.decode())
        // An incomplete frame at EOF is replayed on the next connection.
        return
      }
      consume(decoder.decode(value, {stream: true}))
    }
  } finally {
    signal?.removeEventListener('abort', abort)
    try { await reader.cancel() } finally { reader.releaseLock() }
  }
}

export function createApi(auth: SessionAuth, transport: Transport = {}) {
  const fetcher = transport.fetch || globalThis.fetch.bind(globalThis)
  const root = '/api/ai/tasks'
  const path = (id: string) => `${root}/${encodeURIComponent(id)}`
  async function request<T>(url: string, {signal, body, method = 'GET'}: {signal?: AbortSignal, body?: unknown, method?: string} = {}): Promise<T> {
    const token = await auth.getToken()
    signal?.throwIfAborted()
    let response: Response
    try {
      response = await fetcher(url, {
        method, signal,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(body === undefined ? {} : {'Content-Type': 'application/json'})
        },
        ...(body === undefined ? {} : {body: JSON.stringify(body)})
      })
    } catch (error) {
      if ((error instanceof DOMException || error instanceof Error) && error.name === 'AbortError') throw error
      throw new ApiError('서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요.')
    }
    if (response.status === 401) auth.invalidate()
    const text = await response.text()
    let data
    try { data = text ? JSON.parse(text) : null }
    catch { throw new ApiError('서버 응답 형식이 올바르지 않습니다.', response.status) }
    if (!response.ok) {
      const detail = data?.detail ?? data?.error
      throw new ApiError(typeof detail === 'string' ? detail :
        `요청을 처리하지 못했습니다 (${response.status}).`, response.status)
    }
    return data as T
  }
  return {
    list: (signal?: AbortSignal) => request<Task[]>(root, {signal}),
    detail: (id: string, signal?: AbortSignal) => request<Task>(path(id), {signal}),
    events: (id: string, after: number, signal?: AbortSignal) => request<TaskEvent[]>(`${path(id)}/events?after=${after}`, {signal}),
    create: (question: string, signal?: AbortSignal) => request<{taskId: string}>(root, {method: 'POST', body: {question}, signal}),
    message: (id: string, text: string, signal?: AbortSignal) => request<unknown>(`${path(id)}/messages`, {method: 'POST', body: {text}, signal}),
    approval: (id: string, body: ApprovalBody, signal?: AbortSignal) => request<unknown>(`${path(id)}/approval`, {method: 'POST', body, signal}),
    sops: (signal?: AbortSignal) => request<SopSummary[]>('/api/sops', {signal}),
    sop: (id: string, signal?: AbortSignal) => request<Sop>(`/api/sops/${encodeURIComponent(id)}`, {signal}),
    stream(id: string, after: number, {signal, onEvent, onError, onToken}: StreamHandlers) {
      const controller = new AbortController()
      const close = () => {
        controller.abort()
        signal?.removeEventListener('abort', close)
      }
      if (signal?.aborted) { close(); return close }
      signal?.addEventListener('abort', close, {once: true})
      void (async () => {
        let cursor = after
        let token = await auth.getToken()
        while (!controller.signal.aborted) {
          const response = await fetcher(streamUrl(id, cursor), {
            headers: {Authorization: `Bearer ${token}`, Accept: 'text/event-stream'},
            signal: controller.signal, cache: 'no-store',
          })
          if (response.status === 401) auth.invalidate()
          if (!response.ok) throw new ApiError(`진행 연결을 열지 못했습니다 (${response.status}).`, response.status)
          if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
            throw new ApiError('진행 연결 응답 형식이 올바르지 않습니다.')
          }
          let terminal = false
          await readEventStream(response.body, {
            signal: controller.signal, onToken,
            onEvent(event) {
              if (controller.signal.aborted || event.seq <= cursor) return
              cursor = event.seq
              terminal = ['DONE', 'INCOMPLETE', 'FAILED'].includes(event.type)
              onEvent(event)
            },
          })
          if (controller.signal.aborted || terminal) return
          const updated = await auth.getToken()
          if (updated === token) throw new ApiError('진행 연결이 끊겼습니다. 다시 연결해 주세요.')
          token = updated
        }
      })().catch((error: unknown) => {
        const cancelled = controller.signal.aborted
        close()
        if (!cancelled && !((error instanceof DOMException || error instanceof Error) && error.name === 'AbortError')) {
          onError(error instanceof ApiError ? error : new ApiError('진행 연결을 읽지 못했습니다. 다시 연결해 주세요.'))
        }
      })
      return close
    }
  }
}

export type Api = ReturnType<typeof createApi>

// A sequence is the stable identity across detail replay and live reconnect.
export function mergeEvents(previous: TaskEvent[], incoming: TaskEvent[]): TaskEvent[] {
  const events = new Map(previous.map(event => [Number(event.seq), event]))
  incoming.forEach(event => {
    const seq = Number(event.seq)
    if (Number.isSafeInteger(seq) && seq > 0) events.set(seq, {...event, seq})
  })
  return [...events.values()].sort((a, b) => a.seq - b.seq)
}
