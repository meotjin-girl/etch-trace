import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError } from '@/api/client'
import { activeRun } from '@/api/agent-server'
import type { InvestigationSummary, LiveInvestigation } from '@/api/live-models'
import type { ThreadMessage } from '@/api/thread-messages'
import { useIdentityStore } from './identity'

export const useLiveInvestigationsStore = defineStore('live-investigations', () => {
  const records = ref<InvestigationSummary[]>([])
  const detail = ref<LiveInvestigation | null>(null)
  const messages = ref<ThreadMessage[]>([])
  const draft = ref('')
  const listError = ref(''), error = ref('')
  const loadingList = ref(false), loading = ref(false), busy = ref(false), approving = ref(false)
  let listController: AbortController | undefined
  let controller: AbortController | undefined
  const canSend = computed(() => Boolean(detail.value) && !loading.value && !busy.value && !approving.value &&
    useIdentityStore().status === 'authenticated')
  const message = (cause: unknown) => cause instanceof Error ? cause.message : '요청에 실패했습니다. 다시 연결해 주세요.'
  const current = (request: AbortController) => controller === request && !request.signal.aborted

  async function refreshList() {
    listController?.abort()
    const request = listController = new AbortController()
    loadingList.value = true
    listError.value = ''
    try {
      const result = await useIdentityStore().liveApi.list(request.signal)
      if (listController === request && !request.signal.aborted) records.value = result
    } catch (cause) {
      if (listController === request && !request.signal.aborted) listError.value = message(cause)
    } finally {
      if (listController === request) loadingList.value = false
    }
  }
  async function refreshDetail(request: AbortController) {
    const id = detail.value?.id
    if (!id) return
    const result = await useIdentityStore().liveApi.detail(id, request.signal)
    if (current(request)) detail.value = result
  }
  function stream(request: AbortController) {
    return {signal:request.signal, onMessages(value: ThreadMessage[]) {
      if (current(request)) messages.value = value
    }}
  }
  async function syncThread(request: AbortController) {
    const id = detail.value?.thread_id
    if (!id) return
    const result = await useIdentityStore().agentApi.state(id, request.signal)
    if (current(request)) messages.value = result
  }
  async function finishRun(request: AbortController) {
    if (!current(request) || !detail.value) return
    const threadId = detail.value.thread_id
    // Business persistence and conversation history are independent authorities.
    await Promise.all([refreshDetail(request), syncThread(request)])
    if (!current(request)) return
    const runs = await useIdentityStore().agentApi.runs(threadId, request.signal)
    if (activeRun(runs)) throw new ApiError('실행은 계속 진행 중입니다. 다시 연결해 주세요.')
    const latest = runs[0]
    if (latest && ['error', 'timeout', 'interrupted'].includes(latest.status)) {
      throw new ApiError('실행이 완료되지 않았습니다. 대화를 확인하고 다시 질문해 주세요.')
    }
  }
  async function open(id: string) {
    controller?.abort()
    const request = controller = new AbortController()
    if (detail.value?.id !== id) {
      detail.value = null
      messages.value = []
      draft.value = ''
    }
    error.value = ''
    loading.value = true
    busy.value = false
    approving.value = false
    try {
      const result = await useIdentityStore().liveApi.detail(id, request.signal)
      if (!current(request)) return
      detail.value = result
      const api = useIdentityStore().agentApi
      const [history, runs] = await Promise.all([
        api.state(result.thread_id, request.signal), api.runs(result.thread_id, request.signal),
      ])
      if (!current(request)) return
      messages.value = history
      loading.value = false
      const run = activeRun(runs)
      if (run) {
        busy.value = true
        try { await api.join(result.thread_id, run.run_id, stream(request)) }
        finally { await finishRun(request) }
      }
    } catch (cause) {
      if (current(request)) error.value = message(cause)
    } finally {
      if (current(request)) { loading.value = false; busy.value = false }
    }
  }
  async function send() {
    const content = draft.value.trim(), selected = detail.value, request = controller
    if (!content || !canSend.value || !selected || !request) return
    busy.value = true
    error.value = ''
    const api = useIdentityStore().agentApi
    try {
      const runs = await api.runs(selected.thread_id, request.signal)
      if (!current(request)) return
      const run = activeRun(runs)
      if (run) {
        await api.join(selected.thread_id, run.run_id, stream(request))
      } else {
        try {
          await api.send(selected.thread_id, content, {...stream(request), onAccepted() {
            if (current(request) && draft.value.trim() === content) draft.value = ''
          }})
        } catch (cause) {
          if (!(cause instanceof ApiError) || cause.status !== 409) throw cause
          const running = activeRun(await api.runs(selected.thread_id, request.signal))
          if (!running) throw cause
          await api.join(selected.thread_id, running.run_id, stream(request))
        }
      }
    } catch (cause) {
      if (current(request)) error.value = message(cause)
    } finally {
      try { await finishRun(request) }
      catch (cause) { if (current(request)) error.value = message(cause) }
      if (current(request)) busy.value = false
    }
  }
  async function approve(candidateId: string) {
    const selected = detail.value, request = controller
    if (!selected || !request || selected.approval || approving.value || busy.value || loading.value) return
    if (!selected.candidates.some(candidate => candidate.id === candidateId)) return
    approving.value = true
    error.value = ''
    try {
      const snapshot = await useIdentityStore().liveApi.approve(selected.id, {
        candidate_id:candidateId, expected_revision:selected.revision, comment:'',
      }, request.signal)
      if (current(request) && detail.value) detail.value = {...detail.value, approval:snapshot}
      await refreshDetail(request)
    } catch (cause) {
      if (!current(request)) return
      error.value = message(cause)
      if (cause instanceof ApiError && cause.status === 409) {
        error.value = '다른 사용자가 조사 내용을 변경하거나 승인했습니다. 최신 내용을 확인해 주세요.'
        try { await refreshDetail(request) }
        catch (refreshError) { if (current(request)) error.value = message(refreshError) }
      }
    } finally { if (current(request)) approving.value = false }
  }
  function close() {
    controller?.abort()
    controller = undefined
    detail.value = null
    messages.value = []
    draft.value = ''
    error.value = ''
    loading.value = busy.value = approving.value = false
  }
  function reset() {
    close()
    listController?.abort()
    listController = undefined
    records.value = []
    loadingList.value = false
    listError.value = ''
  }
  return {records, detail, messages, draft, listError, error, loadingList, loading,
    busy, approving, canSend, refreshList, open, send, approve, close, reset}
})
