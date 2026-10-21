import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Task } from '@/api/types'
import { useIdentityStore } from './identity'
import { useUiStore } from './ui'

const LEGACY_KEY = 'etch-investigation-records-v1'

// Old browser-only records: shown read-only, never migrated or treated as approved.
export function legacyRecords(): Task[] {
  try {
    const records = JSON.parse(localStorage.getItem(LEGACY_KEY) || '[]')
    return Array.isArray(records) ? records.filter(item => item && typeof item === 'object').map((item, index) => ({
      ...item, id:`legacy-${index}`, legacy:true, legacyId:item.id,
      status:'로컬 미검증', question:item.context?.symptom || '기존 로컬 기록',
      created_at:item.approvedAt,
      report:{context:item.context, metrics:item.metrics, causeCases:item.causes,
        documents:item.documents, docIds:(item.documents || []).map((doc: {id: string}) => doc.id),
        summary:'이전 브라우저에서 저장한 읽기 전용 기록입니다. 서버에서 검증된 승인이 아닙니다.'}
    })) : []
  } catch { return [] }
}

export const useRecordsStore = defineStore('records', () => {
  const records = ref<Task[]>([])
  const selected = ref<Task | null>(null)
  const detailStatus = ref<'idle' | 'loading' | 'error'>('idle')
  const refreshing = ref(false)
  // Set by RecordsView so background refreshes re-open the visible detail only.
  const visible = ref(false)
  let listController: AbortController | null = null
  let detailController: AbortController | null = null

  const serverCount = computed(() => records.value.filter(item => !item.legacy).length)

  async function refresh() {
    listController?.abort()
    const controller = listController = new AbortController()
    const api = useIdentityStore().api
    refreshing.value = true
    try {
      const list = await api.list(controller.signal)
      if (controller !== listController) return
      records.value = [...list, ...legacyRecords()]
      if (visible.value && selected.value) select(selected.value.id)
    } catch (error) {
      if (controller === listController) {
        if (!records.value.length) records.value = legacyRecords()
        useUiStore().notify(error)
      }
    } finally { if (controller === listController) refreshing.value = false }
  }

  async function select(id: string) {
    detailController?.abort()
    const controller = detailController = new AbortController()
    const item = records.value.find(record => record.id === id)
    if (!item) return
    selected.value = item
    if (item.legacy) { detailStatus.value = 'idle'; return }
    detailStatus.value = 'loading'
    try {
      const detail = await useIdentityStore().api.detail(id, controller.signal)
      if (controller !== detailController) return
      selected.value = detail
      detailStatus.value = 'idle'
    } catch (error) {
      if (controller === detailController) {
        detailStatus.value = 'error'
        useUiStore().notify(error)
      }
    }
  }

  function abortDetail() {
    detailController?.abort()
    detailController = null
  }
  function abort() {
    listController?.abort()
    listController = null
    refreshing.value = false
    abortDetail()
  }
  function clear() {
    records.value = []
    selected.value = null
    detailStatus.value = 'idle'
  }

  return {records, selected, detailStatus, refreshing, visible, serverCount, refresh, select, abortDetail, abort, clear}
})
