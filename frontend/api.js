export const EVENT_TYPES = [
  'QUEUED', 'RUNNING', 'SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED',
  'QUESTION', 'APPROVAL_REQUIRED', 'DONE', 'INCOMPLETE', 'FAILED', 'REVIEWED'
];

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function streamUrl(id, after = 0) {
  return `/api/ai/tasks/${encodeURIComponent(id)}/stream?after=${encodeURIComponent(after)}`;
}

// Each connection owns its decoder and SSE field state, including a CR split
// from the next chunk's LF. Empty data fields still participate in multiline data.
export async function readEventStream(body, {signal, onEvent}) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let line = '', data = [], type = '', lastId = '', skipLF = false;
  function dispatch() {
    if (!data.length) { type = ''; return; }
    const value = JSON.parse(data.join('\n'));
    const seq = Number(value.seq ?? lastId);
    if (!Number.isSafeInteger(seq) || seq < 1) throw new ApiError('진행 이벤트 순서가 올바르지 않습니다.');
    onEvent({seq, type:value.type || type || 'message',
      payload:value.payload ?? value, created_at:value.created_at});
    data = [];
    type = '';
  }
  function consumeLine() {
    if (!line) dispatch();
    else if (!line.startsWith(':')) {
      const colon = line.indexOf(':');
      const field = colon < 0 ? line : line.slice(0, colon);
      let value = colon < 0 ? '' : line.slice(colon + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'data') data.push(value);
      if (field === 'event') type = value;
      if (field === 'id' && !value.includes('\0')) lastId = value;
    }
    line = '';
  }
  function consume(chunk) {
    for (const char of chunk) {
      if (signal?.aborted) return;
      if (skipLF) {
        skipLF = false;
        if (char === '\n') continue;
      }
      if (char === '\r' || char === '\n') {
        consumeLine();
        skipLF = char === '\r';
      } else line += char;
    }
  }
  const abort = () => { reader.cancel().catch(() => {}); };
  signal?.addEventListener('abort', abort, {once:true});
  try {
    if (signal?.aborted) return;
    while (!signal?.aborted) {
      const {value, done} = await reader.read();
      if (signal?.aborted) return;
      if (done) {
        consume(decoder.decode());
        if (line) consumeLine();
        dispatch();
        return;
      }
      consume(decoder.decode(value, {stream:true}));
    }
  } finally {
    signal?.removeEventListener('abort', abort);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export function createApi(auth, transport = {}) {
  const fetcher = transport.fetch || globalThis.fetch.bind(globalThis);
  const root = '/api/ai/tasks';
  const path = id => `${root}/${encodeURIComponent(id)}`;
  function checkAuth(response) {
    if (response.status === 401) auth.invalidate();
  }
  async function request(url, {signal, body, method = 'GET'} = {}) {
    const token = await auth.getToken();
    signal?.throwIfAborted();
    let response;
    try {
      response = await fetcher(url, {
        method, signal,
        headers: {
          Authorization:`Bearer ${token}`,
          ...(body === undefined ? {} : {'Content-Type':'application/json'})
        },
        ...(body === undefined ? {} : {body:JSON.stringify(body)})
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요.');
    }
    checkAuth(response);
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : null; }
    catch { throw new ApiError('서버 응답 형식이 올바르지 않습니다.', response.status); }
    if (!response.ok) {
      const detail = data?.detail ?? data?.error;
      throw new ApiError(typeof detail === 'string' ? detail :
        `요청을 처리하지 못했습니다 (${response.status}).`, response.status);
    }
    return data;
  }
  return {
    list: signal => request(root, {signal}),
    detail: (id, signal) => request(path(id), {signal}),
    events: (id, after, signal) => request(`${path(id)}/events?after=${after}`, {signal}),
    create: (question, signal) => request(root, {method:'POST', body:{question}, signal}),
    message: (id, text, signal) => request(`${path(id)}/messages`, {method:'POST', body:{text}, signal}),
    approval: (id, body, signal) => request(`${path(id)}/approval`, {method:'POST', body, signal}),
    stream(id, after, {signal, onEvent, onError}) {
      const controller = new AbortController();
      const close = () => {
        controller.abort();
        signal?.removeEventListener('abort', close);
      };
      if (signal?.aborted) { close(); return close; }
      signal?.addEventListener('abort', close, {once:true});
      (async () => {
        let cursor = after;
        let token = await auth.getToken();
        while (!controller.signal.aborted) {
          const response = await fetcher(streamUrl(id, cursor), {
            headers:{Authorization:`Bearer ${token}`, Accept:'text/event-stream'},
            signal:controller.signal, cache:'no-store'
          });
          checkAuth(response);
          if (!response.ok) throw new ApiError(`진행 연결을 열지 못했습니다 (${response.status}).`, response.status);
          if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
            throw new ApiError('진행 연결 응답 형식이 올바르지 않습니다.');
          }
          await readEventStream(response.body, {
            signal:controller.signal,
            onEvent(event) {
              if (controller.signal.aborted || event.seq <= cursor) return;
              cursor = event.seq;
              onEvent(event);
            }
          });
          if (controller.signal.aborted) return;
          const updated = await auth.getToken();
          // A clean JWT-expiry close reconnects only with a different token.
          // Early EOF, auth denials, and network errors require explicit retry.
          if (updated === token) throw new ApiError('진행 연결이 끊겼습니다. 다시 연결해 주세요.');
          token = updated;
        }
      })().catch(error => {
        const cancelled = controller.signal.aborted;
        close();
        if (!cancelled && error.name !== 'AbortError') {
          onError(error instanceof ApiError ? error : new ApiError('진행 연결을 읽지 못했습니다. 다시 연결해 주세요.'));
        }
      });
      return close;
    }
  };
}

export function mergeEvents(previous, incoming) {
  const events = new Map(previous.map(event => [Number(event.seq), event]));
  incoming.forEach(event => {
    const seq = Number(event.seq);
    if (Number.isSafeInteger(seq) && seq > 0) events.set(seq, {...event, seq});
  });
  return [...events.values()].sort((a, b) => a.seq - b.seq);
}
