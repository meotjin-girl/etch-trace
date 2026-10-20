<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RecordDetail from '@/components/RecordDetail.vue'
import { date, shortId, statuses } from '@/lib/format'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'
import { useUiStore } from '@/stores/ui'

const records = useRecordsStore()
const investigation = useInvestigationStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()
const routeId = () => route.params.id as string | undefined

onMounted(async () => {
  records.visible = true
  await records.refresh()
  if (routeId()) records.select(routeId()!)
})
onUnmounted(() => { records.visible = false })
watch(routeId, id => { if (id) records.select(id) })

function refresh() {
  ui.clearError()
  records.refresh()
}
function start() {
  investigation.reset()
  router.push('/')
}
</script>

<template>
  <section id="recordsPage" class="records-page">
    <!-- No records at all: a bare centered message instead of the list/detail boxes. -->
    <div v-if="!records.records.length" class="records-empty records-empty-page">
      <strong>조사 기록이 없습니다</strong>
      <p>모든 서버 상태와 기존 로컬 기록을 표시합니다.</p>
      <div class="records-empty-actions">
        <button type="button" @click="start">이상 조사 시작</button>
        <button type="button" class="secondary-button" :disabled="records.refreshing" @click="refresh"><i class="fi-rr-refresh" aria-hidden="true"></i> 새로고침</button>
      </div>
    </div>
    <template v-else>
      <div class="records-heading">
        <div>
          <button type="button" class="secondary-button" :disabled="records.refreshing" @click="refresh"><i class="fi-rr-refresh" aria-hidden="true"></i> 새로고침</button>
          <span class="record-count">{{ records.records.length }}건 (로컬 포함)</span>
        </div>
      </div>
      <div class="records-layout">
        <div class="record-list">
          <RouterLink v-for="item in records.records" :key="item.id" v-slot="{ navigate }" :to="`/records/${encodeURIComponent(item.id)}`" custom>
            <button type="button" class="record-list-item" :class="{active: records.selected?.id === item.id}" @click="navigate">
              <header>
                <span class="record-id" :title="item.id">#{{ item.legacyId || shortId(item.id) }}</span>
                <span class="record-status">{{ statuses[item.status] || item.status }}</span>
              </header>
              <strong class="record-title">{{ item.question }}</strong>
              <small>{{ date(item.created_at) }}{{ item.legacy ? ' · 읽기 전용 로컬 기록' : '' }}</small>
            </button>
          </RouterLink>
        </div>
        <article class="record-detail">
          <template v-if="records.detailStatus === 'loading'">조사 상세를 불러오는 중…</template>
          <template v-else-if="records.detailStatus === 'error'">상세를 불러오지 못했습니다. 기록을 다시 선택해 주세요.</template>
          <RecordDetail v-else-if="records.selected" :task="records.selected" />
          <div v-else class="records-empty">
            <strong>조사 기록을 선택해 주세요</strong>
            <p>모든 서버 상태와 기존 로컬 기록을 표시합니다.</p>
            <button type="button" @click="start">이상 조사 시작</button>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>
