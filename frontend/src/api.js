import { reactive } from 'vue'

// 목업 인증: 이름 + 역할을 localStorage에 보관 (Supabase Auth로 교체 예정)
function load() {
  try { return JSON.parse(localStorage.getItem('trace.user')) || {} } catch { return {} }
}
export const session = reactive(load())
export const ROLES = {
  worker: { label: '작업자', home: '/worker', desc: '이상 run 조사 요청, 내 요청 진행 확인' },
  engineer: { label: '공정 엔지니어', home: '/engineer', desc: '조사 과정 관찰, 보고서 검토·수정 요청·승인' },
  admin: { label: '관리자', home: '/admin', desc: '전체 이력, 승인 기록, 문서 색인, Agent 지표' },
}

export function login(name, role) {
  Object.assign(session, { name, role })
  try { localStorage.setItem('trace.user', JSON.stringify(session)) } catch {}
}
export function logout() {
  delete session.name
  delete session.role
  try { localStorage.removeItem('trace.user') } catch {}
}

async function req(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Name': encodeURIComponent(session.name || ''),
      'X-User-Role': session.role || '',
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `요청 실패 (${res.status})`)
  return data
}

export const api = {
  createTask: (b) => req('POST', '/api/ai/tasks', b),
  tasks: (mine = false) => req('GET', `/api/ai/tasks${mine ? '?mine=true' : ''}`),
  task: (id) => req('GET', `/api/ai/tasks/${id}`),
  approve: (id, action, comment = '') => req('POST', `/api/ai/tasks/${id}/approval`, { action, comment }),
  runs: (q) => req('GET', `/api/runs?q=${encodeURIComponent(q)}`),
  nearFaults: () => req('GET', '/api/runs/near-faults'),
  overview: () => req('GET', '/api/admin/overview'),
}

export const EVENTS = ['QUEUED', 'PLAN', 'TOOL_START', 'TOOL_END', 'TOKEN', 'APPROVAL_REQUIRED', 'REVIEWED', 'DONE', 'FAILED']

// SSE 구독. EventSource는 헤더를 못 보내서 쿼리로 사용자 전달
export function subscribe(id, onEvent) {
  const q = new URLSearchParams({ user_name: session.name, user_role: session.role })
  const es = new EventSource(`/api/ai/tasks/${id}/stream?${q}`)
  for (const type of EVENTS) {
    es.addEventListener(type, (e) => {
      onEvent({ seq: Number(e.lastEventId), type, ...JSON.parse(e.data) })
      if (type === 'DONE' || type === 'FAILED') es.close()
    })
  }
  return () => es.close()
}

export const STATUS = {
  QUEUED: { label: '대기', tone: 'neutral' },
  RUNNING: { label: '조사 중', tone: 'info' },
  WAITING_APPROVAL: { label: '검토 대기', tone: 'warn' },
  DONE: { label: '완료', tone: 'ok' },
  FAILED: { label: '실패', tone: 'bad' },
}

export const fmtTime = (t) => (t ? new Date(t).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '')
