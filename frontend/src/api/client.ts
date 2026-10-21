import type { ApprovalBody, Identity, Sop, SopSummary, Task, TaskEvent } from './types'

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
  EventSource?: new (url: string) => EventSourceLike
}

export interface EventSourceLike {
  addEventListener(type: string, listener: (event: MessageEvent) => void): void
  onmessage: ((event: MessageEvent) => void) | null
  onerror: ((event: Event) => void) | null
  close(): void
}

interface StreamHandlers {
  signal?: AbortSignal
  onEvent: (event: TaskEvent) => void
  onError: (error: ApiError) => void
  // Proposed TOKEN events: unsaved text deltas without a sequence.
  onToken?: (delta: string, target: string) => void
}

// EventSource cannot set headers. Keep its mock identity query transport here.
export function streamUrl(id: string, identity: Identity, after = 0) {
  const query = new URLSearchParams({
    user_name: identity.name, user_role: identity.role, after: String(after)
  })
  return `/api/ai/tasks/${encodeURIComponent(id)}/stream?${query}`
}

export function createApi(identity: Identity, transport: Transport = {}) {
  const fetcher = transport.fetch || globalThis.fetch.bind(globalThis)
  const Source = transport.EventSource || (globalThis.EventSource as unknown as NonNullable<Transport['EventSource']>)
  const root = '/api/ai/tasks'
  const path = (id: string) => `${root}/${encodeURIComponent(id)}`
  async function request<T>(url: string, {signal, body, method = 'GET'}: {signal?: AbortSignal, body?: unknown, method?: string} = {}): Promise<T> {
    let response: Response
    try {
      response = await fetcher(url, {
        method, signal,
        headers: {
          'X-User-Name': encodeURIComponent(identity.name),
          'X-User-Role': identity.role,
          ...(body === undefined ? {} : {'Content-Type': 'application/json'})
        },
        ...(body === undefined ? {} : {body: JSON.stringify(body)})
      })
    } catch (error) {
      if ((error as Error).name === 'AbortError') throw error
      throw new ApiError('서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요.')
    }
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
      if (signal?.aborted) return () => {}
      const source = new Source(streamUrl(id, identity, after))
      const close = () => {
        source.close()
        signal?.removeEventListener('abort', close)
      }
      signal?.addEventListener('abort', close, {once: true})
      const receive = (event: MessageEvent) => {
        if (signal?.aborted) return
        try {
          const data = JSON.parse(event.data)
          const seq = Number(data.seq ?? event.lastEventId)
          if (!Number.isSafeInteger(seq) || seq < 1) throw new Error('Missing event sequence')
          onEvent({
            seq, type: data.type || event.type,
            payload: data.payload ?? data, created_at: data.created_at
          })
        } catch {
          close()
          onError(new ApiError('진행 이벤트를 읽지 못했습니다. 다시 연결해 주세요.'))
        }
      }
      EVENT_TYPES.forEach(type => source.addEventListener(type, receive))
      // A lost or malformed token is harmless: the next saved event carries the full text.
      source.addEventListener('TOKEN', event => {
        if (signal?.aborted) return
        try {
          const data = JSON.parse(event.data)
          if (typeof data.delta === 'string') onToken?.(data.delta, String(data.target || 'message'))
        } catch { /* ignore */ }
      })
      source.onmessage = receive
      source.onerror = () => {
        close()
        if (!signal?.aborted) onError(new ApiError('진행 연결이 끊겼습니다. 다시 연결하면 이후 이벤트를 복구합니다.'))
      }
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
