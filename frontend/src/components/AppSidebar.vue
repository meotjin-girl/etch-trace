<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { progressStep } from '@/lib/format'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'

defineEmits<{ new: [] }>()
const identity = useIdentityStore()
const investigation = useInvestigationStore()
const records = useRecordsStore()
const route = useRoute()
// Shown on the investigation page, and on records only once a record is opened.
const step = computed(() => {
  if (route.name === 'investigation') return investigation.step
  const record = records.selected
  if (route.name !== 'records' || !route.params.id || !record) return null
  return progressStep(record.events || [], Boolean(record.report))
})
const steps = [
  ['질문 접수', '이상 현상 파악'], ['근거 검색', '사례·문서 조회'],
  ['수치 분석', '편차·z-score'], ['답변 생성', '근거 연결'],
]
const nav = [
  {to: '/', name: 'investigation', icon: 'fi-rr-pulse', label: '이상 조사'},
  {to: '/records', name: 'records', icon: 'fi-rr-time-past', label: '조사 기록'},
  {to: '/sop', name: 'sop', icon: 'fi-rr-book-alt', label: 'SOP 목록'},
]
</script>

<template>
  <aside class="sidebar" aria-label="서비스 탐색">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"><span></span><span></span><span></span></div>
      <div><strong>FAB Insight</strong><small>Etch Investigation</small></div>
    </div>

    <button class="new-investigation" type="button" @click="$emit('new')">
      <i class="fi-rr-plus" aria-hidden="true"></i> 새 조사
    </button>

    <nav class="nav-section" aria-label="조사 메뉴">
      <p class="nav-label">WORKSPACE</p>
      <RouterLink v-for="item in nav" :key="item.name" v-slot="{ navigate }" :to="item.to" custom>
        <button class="nav-item" :class="{active: $route.name === item.name}" type="button" @click="navigate">
          <i class="nav-icon" :class="item.icon" aria-hidden="true"></i> {{ item.label }}
          <em v-if="item.name === 'records'">{{ records.serverCount }}</em>
        </button>
      </RouterLink>
    </nav>

    <div v-if="step" class="process-card">
      <p class="nav-label">현재 조사 단계</p>
      <ol class="steps">
        <li v-for="([title, hint], index) in steps" :key="title"
          :class="{active: index === step - 1, done: index < step - 1}">
          <span>{{ index + 1 }}</span><div><strong>{{ title }}</strong><small>{{ hint }}</small></div>
        </li>
      </ol>
    </div>

    <div class="sidebar-footer">
      <div class="user-card">
        <i class="user-icon fi-rr-circle-user" aria-hidden="true"></i>
        <strong>{{ identity.name }}</strong>
      </div>
      <a class="icon-credit" href="https://www.flaticon.com/uicons" target="_blank" rel="noopener noreferrer">Uicons by Flaticon</a>
    </div>
  </aside>
</template>
