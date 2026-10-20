<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { mergeEvents } from '@/api/client'
import type { Task } from '@/api/types'
import ReportView from '@/components/ReportView.vue'
import { date, eventLine, shortId, statuses } from '@/lib/format'
import { useInvestigationStore } from '@/stores/investigation'

const props = defineProps<{ task: Task }>()
const investigation = useInvestigationStore()
const router = useRouter()

// Saved events already cover messages and reviews (MESSAGE, REVIEWED), in exact order.
const history = computed(() => mergeEvents([], props.task.events || [])
  .map(event => ({seq:event.seq, at:event.created_at, ...eventLine(event)})))

async function resume() {
  if (await investigation.activateTask(props.task.id)) router.push('/')
}
</script>

<template>
  <div class="detail-status">
    <div><p class="eyebrow" :title="task.id">#{{ task.legacyId || shortId(task.id) }}</p><h3>{{ task.question }}</h3></div>
    <span class="approved-badge">{{ statuses[task.status] || task.status }}</span>
  </div>
  <div class="detail-meta">
    <div><span>요청자</span><strong>{{ task.user_name || '기존 로컬 기록' }}</strong></div>
    <div><span>생성</span><strong>{{ date(task.created_at) }}</strong></div>
    <div><span>최근 갱신</span><strong>{{ date(task.updated_at) }}</strong></div>
  </div>
  <p v-if="task.legacy" class="data-notice">읽기 전용 로컬 기록 · 서버 검증 승인 아님</p>
  <div v-else class="record-cta">
    <button type="button" class="record-button" @click="resume">조사 열기 / 이어가기</button>
  </div>
  <ReportView v-if="task.report" :report="task.report" />
  <h4>진행 이력</h4>
  <ol class="timeline">
    <li v-for="item in history" :key="item.seq">
      <div class="timeline-head"><strong>{{ item.title }}</strong><time>{{ date(item.at) }}</time></div>
      <p v-if="item.detail">{{ item.detail }}</p>
    </li>
    <li v-if="!history.length" class="timeline-empty">이력이 없습니다.</li>
  </ol>
</template>
