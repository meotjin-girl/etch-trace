<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AuthGate from '@/components/AuthGate.vue'
import EvidencePanel from '@/components/EvidencePanel.vue'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'
import { useRecordsStore } from '@/stores/records'
import { useUiStore } from '@/stores/ui'

const identity = useIdentityStore()
const investigation = useInvestigationStore()
const records = useRecordsStore()
const live = useLiveInvestigationsStore()
const ui = useUiStore()

function leave() {
  investigation.stopTask()
  records.abort()
  live.reset()
}
onMounted(() => {
  if (identity.status === 'loading') void identity.init()
  window.addEventListener('pagehide', leave)
})
onUnmounted(() => window.removeEventListener('pagehide', leave))
</script>

<template>
  <AuthGate v-if="identity.status !== 'authenticated'" />
  <div v-else class="t-shell">
    <AppSidebar />
    <main v-if="!$route.meta.legacy" class="t-main">
      <RouterView />
    </main>
    <!-- Hidden previous workspace: keeps its own status row and evidence rail. -->
    <div v-else class="legacy-area" :class="{'evidence-closed': ui.evidenceClosed}">
      <main class="workspace">
        <section class="session-controls" aria-label="조사 상태">
          <span role="status">{{ $route.name === 'legacy-records' ? '이전 질문 기반 작업 기록' : investigation.statusText }}</span>
        </section>
        <div class="network-notice" role="alert" :hidden="!ui.networkError">
          <span>{{ ui.networkError }}</span>
          <button type="button" class="secondary-button" @click="investigation.retry()">다시 연결</button>
        </div>
        <RouterView />
      </main>
      <EvidencePanel />
    </div>
  </div>
</template>

<style scoped>
.legacy-area { overflow-y: auto; display: grid; grid-template-columns: minmax(0, 1fr) 330px; min-width: 0; }
.legacy-area.evidence-closed { grid-template-columns: minmax(0, 1fr); }
@media (max-width: 1100px) { .legacy-area { grid-template-columns: minmax(0, 1fr); } }
</style>
