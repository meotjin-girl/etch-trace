import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { headline, parseAlert, stageOf } from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

/** Shared by the step pages of one investigation (/investigations/:id/...). */
export function useInvestigation() {
  const live = useLiveInvestigationsStore()
  const route = useRoute()
  const id = computed(() => typeof route.params.id === 'string' ? route.params.id : '')
  watch(id, value => {
    if (!value) return
    // Moving between steps keeps the open thread; only a different investigation reopens it.
    if (live.detail?.id === value) void live.reload()
    else void live.open(value)
  }, {immediate:true})
  const detail = computed(() => live.detail?.id === id.value ? live.detail : null)
  const parsed = computed(() => detail.value ? parseAlert(detail.value.alert.source_text) : null)
  const head = computed(() => parsed.value ? headline(parsed.value) : null)
  const stage = computed(() => detail.value ? stageOf(detail.value) : null)
  return {live, id, detail, parsed, head, stage}
}
