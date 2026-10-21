import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { mergeEvents } from '@/api/client'
import type { Report, Task, TaskEvent } from '@/api/types'
import { agentFlow, statuses, terminal, text } from '@/lib/format'
import { useIdentityStore } from './identity'
import { useRecordsStore } from './records'
import { useUiStore } from './ui'

const refreshTypes = ['QUESTION', 'APPROVAL_REQUIRED', 'DONE', 'FAILED', 'INCOMPLETE', 'REVIEWED']
const decisions = ['승인', '미승인']

// One chat bubble, derived from saved events so multi-turn order is exact.
export interface ChatItem {
  key: string
  seq?: number
  role: 'user' | 'assistant'
  kind: 'text' | 'question' | 'report' | 'notice'
  text?: string
  missing?: unknown
  report?: Report
}

export const useInvestigationStore = defineStore('investigation', () => {
  const identity = useIdentityStore()
  const records = useRecordsStore()
  const ui = useUiStore()

  const task = ref<Task | null>(null)
  const events = ref<TaskEvent[]>([])
  const after = ref(0)
  const busy = ref(false)
  const draft = ref('')
  // Proposed TOKEN deltas for the reply being written; cleared by the next saved event.
  const streaming = ref<{target: string, text: string} | null>(null)
  // Plain counters, not state: every async result checks them before writing.
  let epoch = 0
  let syncVersion = 0
  let controller = new AbortController()
  let closeStream: (() => void) | null = null

  const isOwner = (item: Task | null | undefined) => item?.user_name === identity.name
  const canReview = (item: Task | null | undefined) =>
    identity.role === 'engineer' && item?.status === 'WAITING_APPROVAL' && !item.legacy

  const canAnswer = (item: Task | null | undefined) => item?.status === 'WAITING_INPUT' && isOwner(item)
  const inputBlocked = computed(() => busy.value ||
    Boolean(task.value && !canAnswer(task.value) && !canReview(task.value)))
  const statusText = computed(() => busy.value ? '요청 전송 중' :
    task.value ? `${statuses[task.value.status] || task.value.status} · ${task.value.id}` : '질문을 입력해 주세요')
  const placeholder = computed(() => {
    const current = task.value
    if (!current) return '특정 이상에 대해 질문해 주세요…'
    if (canReview(current)) return '수정할 내용을 입력하면 미승인으로 보냅니다…'
    if (current.status === 'WAITING_INPUT') return isOwner(current) ? '추가 정보를 입력해 주세요…' : '조사 소유자만 추가 정보를 보낼 수 있습니다'
    return terminal.has(current.status) ? '새 질문은 새 조사를 시작해 주세요' : '에이전트가 작업 중입니다…'
  })
  const flow = computed(() => agentFlow(events.value, task.value?.report))
  const chat = computed<ChatItem[]>(() => {
    const current = task.value
    if (!current) return []
    const items: ChatItem[] = []
    for (const event of events.value) {
      const payload = event.payload || {}
      const base = {key:`e${event.seq}`, seq:event.seq}
      if (event.type === 'QUEUED') items.push({...base, role:'user', kind:'text', text:current.question})
      else if (event.type === 'MESSAGE') items.push({...base, role:'user', kind:'text', text:text(payload.text)})
      else if (event.type === 'QUESTION') items.push({...base, role:'assistant', kind:'question', text:text(payload.text), missing:payload.missing})
      else if (event.type === 'APPROVAL_REQUIRED') items.push({...base, role:'assistant', kind:'report', report:payload.report ?? current.report ?? undefined, text:payload.text})
      else if (event.type === 'REVIEWED') items.push({...base, role:'user', kind:'text',
        text:payload.action === 'approve' ? '승인' : payload.comment ? `미승인 · ${payload.comment}` : '미승인'})
      else if (event.type === 'DONE') items.push({...base, role:'assistant', kind:'notice', text:'조사가 완료되어 기록으로 저장되었습니다.'})
      else if (event.type === 'FAILED' || event.type === 'INCOMPLETE') items.push({...base, role:'assistant', kind:'notice', text:text(payload.error ?? payload.reason)})
    }
    // Before any event arrives (just created or still loading) show the question itself.
    if (!items.length && current.question) items.push({key:'question', role:'user', kind:'text', text:current.question})
    return items
  })
  // Quick replies for the latest pending prompt only. Approval falls back to 승인/미승인
  // so the current backend (no options field) still gets chat buttons.
  const pending = computed(() => {
    const current = task.value
    if (!current || busy.value) return null
    const last = [...events.value].reverse().find(event => event.type === 'QUESTION' || event.type === 'APPROVAL_REQUIRED')
    const options = Array.isArray(last?.payload.options) ? last!.payload.options.map(String) : []
    if (canReview(current)) return {seq:last?.seq, options:options.length ? options : decisions, decision:true}
    if (canAnswer(current) && options.length) return {seq:last?.seq, options, decision:false}
    return null
  })
  function stopTask() {
    epoch++
    records.abortDetail()
    controller.abort()
    controller = new AbortController()
    closeStream?.()
    closeStream = null
    busy.value = false
    streaming.value = null
  }
  function reset() {
    stopTask()
    task.value = null
    records.selected = null
    events.value = []
    after.value = 0
    draft.value = ''
    ui.clearError()
  }
  function applyEvents(incoming: TaskEvent[]) {
    events.value = mergeEvents(events.value, incoming)
    after.value = events.value.at(-1)?.seq || 0
    const current = task.value!
    for (const event of incoming) {
      const payload = event.payload || {}
      const status = ({QUESTION:'WAITING_INPUT', APPROVAL_REQUIRED:'WAITING_APPROVAL'} as Record<string, string>)[event.type]
      if (status) current.status = status
      else if (['QUEUED', 'RUNNING', 'DONE', 'FAILED', 'INCOMPLETE'].includes(event.type)) current.status = event.type
      else if (['SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED'].includes(event.type)) current.status = 'RUNNING'
      if (payload.report) current.report = payload.report
    }
    current.events = events.value
  }
  function connectStream() {
    const current = task.value
    if (!current || terminal.has(current.status)) return
    closeStream?.()
    const started = epoch
    closeStream = identity.api.stream(current.id, after.value, {
      signal:controller.signal,
      onEvent(event) {
        if (started !== epoch || event.seq <= after.value) return
        streaming.value = null
        applyEvents([event])
        if (records.selected?.id === current.id) records.selected = task.value
        if (terminal.has(task.value!.status)) closeStream?.()
        if (refreshTypes.includes(event.type)) {
          records.refresh()
          syncTask(started)
        }
      },
      onError(error) { if (started === epoch) ui.notify(error) },
      onToken(delta, target) {
        if (started !== epoch) return
        const previous = streaming.value?.target === target ? streaming.value.text : ''
        streaming.value = {target, text:previous + delta}
      }
    })
  }
  async function syncTask(started = epoch) {
    const version = ++syncVersion
    const startingSeq = after.value
    try {
      const detail = await identity.api.detail(task.value!.id, controller.signal)
      if (started !== epoch || version !== syncVersion) return
      const live = task.value!
      const liveAdvanced = after.value > startingSeq
      events.value = mergeEvents(detail.events || [], events.value)
      after.value = events.value.at(-1)?.seq || 0
      // Never derive current status from historical approvals after a revision.
      // Events arriving during this request are newer than its snapshot.
      task.value = {...detail,
        status:liveAdvanced ? live.status : detail.status,
        report:liveAdvanced ? live.report : detail.report || live.report,
        events:events.value}
      if (records.selected?.id === detail.id) records.selected = task.value
    } catch (error) { if (started === epoch && version === syncVersion) ui.notify(error) }
  }
  async function activateTask(id: string) {
    stopTask()
    ui.clearError()
    const started = epoch
    task.value = (task.value?.id === id ? task.value : records.records.find(item => item.id === id)) ||
      {id, status:'LOADING'}
    events.value = []
    after.value = 0
    busy.value = true
    try {
      const detail = await identity.api.detail(id, controller.signal)
      if (started !== epoch) return false
      task.value = detail
      events.value = mergeEvents([], detail.events || [])
      after.value = events.value.at(-1)?.seq || 0
      // Detail status is authoritative; replay only builds chronology/progress.
      connectStream()
      return true
    } catch (error) {
      if (started === epoch) ui.notify(error)
      return false
    } finally { if (started === epoch) busy.value = false }
  }
  // Typed text: a new question, an answer to QUESTION, or (while awaiting a decision)
  // a rejection with that text as the revision request. `override` is a quick reply.
  async function submitQuestion(override?: string) {
    const question = (override ?? draft.value).trim()
    if (!question || inputBlocked.value) return
    if (task.value && canReview(task.value)) {
      await decide('revise', question)
      if (override === undefined && !ui.networkError) draft.value = ''
      return
    }
    const started = epoch
    const current = task.value
    busy.value = true
    ui.clearError()
    try {
      if (current) {
        if (!canAnswer(current)) return
        await identity.api.message(current.id, question, controller.signal)
        if (started !== epoch) return
        if (override === undefined) draft.value = ''
        await syncTask(started)
        connectStream()
      } else {
        const created = await identity.api.create(question, controller.signal)
        if (started !== epoch) return
        // Keep the accepted id even if the first detail request fails.
        task.value = {id:created.taskId, question, status:'QUEUED', user_name:identity.name, user_role:identity.role}
        if (override === undefined) draft.value = ''
        await activateTask(created.taskId)
      }
      records.refresh()
    } catch (error) { if (started === epoch) ui.notify(error) }
    finally { if (started === epoch) busy.value = false }
  }
  async function retry() {
    ui.clearError()
    if (task.value) {
      const started = epoch
      try {
        const missed = await identity.api.events(task.value.id, after.value, controller.signal)
        if (started !== epoch) return
        applyEvents(missed.filter(event => Number(event.seq) > after.value))
        await syncTask(started)
        if (started === epoch) connectStream()
      } catch (error) { if (started === epoch) ui.notify(error) }
    }
    records.refresh()
  }

  // Engineer judgement in chat; the agent follows up with its next question.
  async function decide(action: 'approve' | 'revise', comment = '') {
    const current = task.value
    if (!current || !canReview(current) || busy.value) return
    const started = epoch
    busy.value = true
    ui.clearError()
    try {
      await identity.api.approval(current.id, {action, comment}, controller.signal)
      if (started !== epoch) return
      records.refresh()
      await syncTask(started)
      connectStream()
    } catch (error) { if (started === epoch) ui.notify(error) }
    finally { if (started === epoch) busy.value = false }
  }
  function choose(option: string) {
    if (pending.value?.decision) return option === '승인' ? decide('approve') : decide('revise')
    return submitQuestion(option)
  }

  return {
    task, events, after, busy, draft, streaming,
    isOwner, canReview, inputBlocked, statusText, placeholder, flow, chat, pending,
    stopTask, reset, applyEvents, connectStream, syncTask, activateTask, submitQuestion, retry,
    decide, choose
  }
})
