<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import EvidencePanel from '@/components/EvidencePanel.vue'
import AuthGate from '@/components/AuthGate.vue'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'
import { useUiStore } from '@/stores/ui'

const investigation = useInvestigationStore()
const records = useRecordsStore()
const ui = useUiStore()
const router = useRouter()
const identity = useIdentityStore()
watch(() => identity.status, status => {
  if (status === 'authenticated') void records.refresh()
})

async function newInvestigation() {
  investigation.reset()
  await router.push('/')
  document.getElementById('questionInput')?.focus()
}
function leave() {
  investigation.stopTask()
  records.abort()
}

onMounted(() => {
  if (identity.status === 'loading') void identity.init()
  else if (identity.status === 'authenticated') void records.refresh()
  window.addEventListener('pagehide', leave)
})
onUnmounted(() => window.removeEventListener('pagehide', leave))
</script>

<template>
  <AuthGate v-if="identity.status !== 'authenticated'" />
  <div v-else class="app-shell" :class="{'sop-open': $route.name === 'sop', 'evidence-closed': ui.evidenceClosed}">
    <AppSidebar @new="newInvestigation" />

    <main class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">INVESTIGATION ASSISTANT</p>
          <h1>{{ $route.meta.title }}</h1>
        </div>
        <div class="account-controls">
          <span>{{ identity.name }}</span>
          <button type="button" class="secondary-button" @click="identity.logout()">로그아웃</button>
        </div>
      </header>

      <section class="session-controls" aria-label="조사 상태 및 탐색">
        <span class="mobile-navigation">
          <button type="button" class="secondary-button" @click="newInvestigation">새 조사</button>
          <RouterLink v-slot="{ navigate }" to="/" custom><button type="button" class="secondary-button" @click="navigate">이상 조사</button></RouterLink>
          <RouterLink v-slot="{ navigate }" to="/records" custom><button type="button" class="secondary-button" @click="navigate">조사 기록</button></RouterLink>
          <RouterLink v-slot="{ navigate }" to="/sop" custom><button type="button" class="secondary-button" @click="navigate">SOP 목록</button></RouterLink>
        </span>
        <label v-if="$route.name === 'sop'" class="sop-search" for="sopSearch">
          <i class="fi-rr-search" aria-hidden="true"></i>
          <span class="sr-only">문서 검색</span>
          <input id="sopSearch" v-model="ui.sopQuery" type="search" placeholder="문서명, 문서 번호, 키워드 검색" autocomplete="off">
        </label>
        <span v-else-if="$route.name === 'records'">모든 상태의 서버 조사를 열어 대화·진행·검토 이력을 확인하거나 이어갈 수 있습니다.</span>
        <span v-else role="status">{{ investigation.statusText }}</span>
      </section>
      <div class="network-notice" role="alert" :hidden="!ui.networkError">
        <span>{{ ui.networkError }}</span>
        <button type="button" class="secondary-button" @click="investigation.retry()">다시 연결</button>
      </div>

      <RouterView />
    </main>

    <EvidencePanel />
  </div>

</template>

<style scoped>
.topbar { height: auto; min-height: 84px; }
.account-controls { display: flex; align-items: center; gap: 12px; min-width: 0; font-size: 14px; }
.account-controls span { overflow-wrap: anywhere; }
@media (max-width: 720px) {
  .topbar { min-height: 72px; flex-wrap: wrap; gap: 12px; }
}
</style>
