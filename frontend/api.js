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

// EventSource cannot set headers. Keep its mock identity query transport here.
export function streamUrl(id, identity, after = 0) {
  const query = new URLSearchParams({
    user_name: identity.name, user_role: identity.role, after: String(after)
  });
  return `/api/ai/tasks/${encodeURIComponent(id)}/stream?${query}`;
}

export function createApi(identity, transport = {}) {
  const fetcher = transport.fetch || globalThis.fetch.bind(globalThis);
  const Source = transport.EventSource || globalThis.EventSource;
  const root = '/api/ai/tasks';
  const path = id => `${root}/${encodeURIComponent(id)}`;
  async function request(url, {signal, body, method = 'GET'} = {}) {
    let response;
    try {
      response = await fetcher(url, {
        method, signal,
        headers: {
          'X-User-Name': encodeURIComponent(identity.name),
          'X-User-Role': identity.role,
          ...(body === undefined ? {} : {'Content-Type': 'application/json'})
        },
        ...(body === undefined ? {} : {body: JSON.stringify(body)})
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요.');
    }
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
    create: (question, signal) => request(root, {method: 'POST', body: {question}, signal}),
    message: (id, text, signal) => request(`${path(id)}/messages`, {method: 'POST', body: {text}, signal}),
    approval: (id, body, signal) => request(`${path(id)}/approval`, {method: 'POST', body, signal}),
    stream(id, after, {signal, onEvent, onError}) {
      if (signal?.aborted) return () => {};
      const source = new Source(streamUrl(id, identity, after));
      const close = () => {
        source.close();
        signal?.removeEventListener('abort', close);
      };
      signal?.addEventListener('abort', close, {once: true});
      const receive = event => {
        if (signal?.aborted) return;
        try {
          const data = JSON.parse(event.data);
          const seq = Number(data.seq ?? event.lastEventId);
          if (!Number.isSafeInteger(seq) || seq < 1) throw new Error('Missing event sequence');
          onEvent({
            seq, type: data.type || event.type,
            payload: data.payload ?? data, created_at: data.created_at
          });
        } catch {
          close();
          onError(new ApiError('진행 이벤트를 읽지 못했습니다. 다시 연결해 주세요.'));
        }
      };
      EVENT_TYPES.forEach(type => source.addEventListener(type, receive));
      source.onmessage = receive;
      source.onerror = () => {
        close();
        if (!signal?.aborted) onError(new ApiError('진행 연결이 끊겼습니다. 다시 연결하면 이후 이벤트를 복구합니다.'));
      };
      return close;
    }
  };
}

// A sequence is the stable identity across detail replay and live reconnect.
export function mergeEvents(previous, incoming) {
  const events = new Map(previous.map(event => [Number(event.seq), event]));
  incoming.forEach(event => {
    const seq = Number(event.seq);
    if (Number.isSafeInteger(seq) && seq > 0) events.set(seq, {...event, seq});
  });
  return [...events.values()].sort((a, b) => a.seq - b.seq);
}
