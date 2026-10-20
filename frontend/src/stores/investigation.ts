import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { mergeEvents } from '@/api/client'
import type { Task, TaskEvent } from '@/api/types'
import { progressStep, statuses, terminal, text } from '@/lib/format'
import { useIdentityStore } from './identity'
import { useRecordsStore } from './records'
import { useUiStore } from './ui'

const refreshTypes = ['QUESTION', 'APPROVAL_REQUIRED', 'DONE', 'FAILED', 'INCOMPLETE', 'REVIEWED']

export const useInvestigationStore = defineStore('investigation', () => {
  const identity = useIdentityStore()
  const records = useRecordsStore()
  const ui = useUiStore()

  const task = ref<Task | null>(null)
  const events = ref<TaskEvent[]>([])
  const after = ref(0)
  const busy = ref(false)
  const draft = ref('')
  const review = reactive({
    task: null as Task | null, time: '', lot: '', comment: '', notice: '', busy: false
  })
  // Plain counters, not state: every async result checks them before writing.
  let epoch = 0
  let syncVersion = 0
  let controller = new AbortController()
  let closeStream: (() => void) | null = null

  const isOwner = (item: Task | null | undefined) => item?.user_name === identity.name
  const canReview = (item: Task | null | undefined) =>
    identity.role === 'engineer' && item?.status === 'WAITING_APPROVAL' && !item.legacy

  const inputBlocked = computed(() => busy.value ||
    Boolean(task.value && !(task.value.status === 'WAITING_INPUT' && isOwner(task.value))))
  const statusText = computed(() => busy.value ? '요청 전송 중' :
    task.value ? `${statuses[task.value.status] || task.value.status} · ${task.value.id}` : '질문을 입력해 주세요')
  const placeholder = computed(() => task.value?.status === 'WAITING_INPUT' ?
    (isOwner(task.value) ? '추가 정보를 입력해 주세요…' : '조사 소유자만 추가 정보를 보낼 수 있습니다') :
    task.value ? '새 질문은 새 조사를 시작해 주세요' : '특정 이상에 대해 질문해 주세요…')
  const step = computed(() => progressStep(events.value, Boolean(task.value?.report)))
  // QUESTION is the authoritative follow-up prompt, including missing fields.
  const followUps = computed(() => events.value.filter(event => event.type === 'QUESTION' &&
    !(task.value?.messages || []).some(item => item.role === 'assistant' &&
      (item.text ?? item.content) === event.payload.text)))
  const failure = computed(() => {
    const last = events.value.at(-1)
    return last && ['FAILED', 'INCOMPLETE'].includes(last.type) ?
      text(last.payload.error ?? last.payload.reason) : null
  })

  function closeReview() { review.task = null }
  function stopTask() {
    epoch++
    records.abortDetail()
    controller.abort()
    controller = new AbortController()
    closeStream?.()
    closeStream = null
    busy.value = false
    review.busy = false
    closeReview()
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
        applyEvents([event])
        if (records.selected?.id === current.id) records.selected = task.value
        if (terminal.has(task.value!.status)) closeStream?.()
        if (refreshTypes.includes(event.type)) {
          records.refresh()
          syncTask(started)
        }
      },
      onError(error) { if (started === epoch) ui.notify(error) }
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
  async function submitQuestion() {
    const question = draft.value.trim()
    if (!question || inputBlocked.value) return
    const started = epoch
    const current = task.value
    busy.value = true
    ui.clearError()
    try {
      if (current) {
        if (current.status !== 'WAITING_INPUT' || !isOwner(current)) return
        await identity.api.message(current.id, question, controller.signal)
        if (started !== epoch) return
        draft.value = ''
        await syncTask(started)
        connectStream()
      } else {
        const created = await identity.api.create(question, controller.signal)
        if (started !== epoch) return
        // Keep the accepted id even if the first detail request fails.
        task.value = {id:created.taskId, question, status:'QUEUED', user_name:identity.name, user_role:identity.role}
        draft.value = ''
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

  function openReview(item: Task | null | undefined) {
    if (!item?.report || item.legacy) return
    Object.assign(review, {task:item, time:'', lot:'', comment:'',
      notice:canReview(item) ? '엔지니어 권한으로 서버에 검토를 제출합니다.' :
        '검토 대기 상태의 조사만 엔지니어가 승인하거나 수정 요청할 수 있습니다. 현재는 읽기 전용입니다.'})
  }
  // Returns false when the form needs attention (missing revise comment).
  async function submitReview(action: string) {
    const item = review.task
    if (!canReview(item) || review.busy || !item) return true
    if (action !== 'approve' && action !== 'revise') return true
    const comment = review.comment.trim()
    if (action === 'revise' && !comment) {
      review.notice = '수정 요청 의견을 입력해 주세요.'
      return false
    }
    const started = epoch
    review.busy = true
    try {
      await identity.api.approval(item.id, {
        action, comment,
        ...(review.time ? {event_time:new Date(review.time).toISOString()} : {}),
        ...(review.lot.trim() ? {lot_id:review.lot.trim()} : {})
      }, controller.signal)
      if (started !== epoch) return true
      closeReview()
      await records.refresh()
      if (task.value?.id === item.id) {
        await syncTask(started)
        connectStream()
      }
      if (records.selected?.id === item.id) await records.select(item.id)
    } catch (error) {
      if (started === epoch) { ui.notify(error); review.notice = (error as Error).message }
    } finally { if (started === epoch) review.busy = false }
    return true
  }

  return {
    task, events, after, busy, draft, review,
    isOwner, canReview, inputBlocked, statusText, placeholder, step, followUps, failure,
    stopTask, reset, applyEvents, connectStream, syncTask, activateTask, submitQuestion, retry,
    openReview, closeReview, submitReview
  }
})
