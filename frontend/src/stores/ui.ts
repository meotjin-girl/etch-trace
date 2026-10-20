import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useInvestigationStore } from './investigation'

export const useUiStore = defineStore('ui', () => {
  // Desktop rail starts visible; the <=1100px drawer starts closed.
  const evidenceClosed = ref(false)
  const evidenceOpen = ref(false)
  // A fresh object per request so repeated clicks on one citation scroll again.
  const highlight = ref<{id: string | null}>({id: null})
  const networkError = ref<string | null>(null)
  // SOP search lives in the top bar row, outside SopView.
  const sopQuery = ref('')

  function openEvidence(id: string | null = null) {
    useInvestigationStore().closeReview()
    evidenceClosed.value = false
    evidenceOpen.value = true
    highlight.value = {id}
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

  return {evidenceClosed, evidenceOpen, highlight, networkError, sopQuery, openEvidence, closeEvidence, notify, clearError}
})
