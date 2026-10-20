import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useInvestigationStore } from './investigation'

export const useUiStore = defineStore('ui', () => {
  // Desktop rail starts visible; the <=1100px drawer starts closed.
  const evidenceClosed = ref(false)
  const evidenceOpen = ref(false)
  const highlightId = ref<string | null>(null)
  const networkError = ref<string | null>(null)

  function openEvidence(id: string | null = null) {
    useInvestigationStore().closeReview()
    evidenceClosed.value = false
    evidenceOpen.value = true
    highlightId.value = id
  }
  function closeEvidence() {
    evidenceClosed.value = true
    evidenceOpen.value = false
  }
  function notify(error: unknown) {
    if ((error as Error).name === 'AbortError') return
    networkError.value = (error as Error).message
  }
  function clearError() { networkError.value = null }

  return {evidenceClosed, evidenceOpen, highlightId, networkError, openEvidence, closeEvidence, notify, clearError}
})
