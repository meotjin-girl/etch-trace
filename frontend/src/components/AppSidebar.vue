<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { agentFlow } from '@/lib/format'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'

defineEmits<{ new: [] }>()
const identity = useIdentityStore()
const investigation = useInvestigationStore()
const records = useRecordsStore()
const route = useRoute()
// Shown on the investigation page, and on records only once a record is opened.
const flow = computed(() => {
  if (route.name === 'investigation') return investigation.flow
  const record = records.selected
  if (route.name !== 'records' || !route.params.id || !record) return null
  return agentFlow(record.events || [], record.report)
})
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

    <div v-if="flow" class="process-card">
      <p class="nav-label">에이전트 흐름</p>
      <ol class="steps">
        <li v-for="(step, index) in flow" :key="step.key" :class="step.state"
          :aria-current="step.state === 'active' ? 'step' : undefined">
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ step.title }}</strong>
            <small :title="step.result || step.hint">{{ step.state === 'stopped' ? '중단됨' : step.result || step.hint }}</small>
          </div>
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
