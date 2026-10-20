<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { mergeEvents } from '@/api/client'
import type { Task } from '@/api/types'
import ReportView from '@/components/ReportView.vue'
import { date, statuses, text } from '@/lib/format'
import { useInvestigationStore } from '@/stores/investigation'

const props = defineProps<{ task: Task }>()
const investigation = useInvestigationStore()
const router = useRouter()

const chronology = computed(() => [
  ...(props.task.messages || []).map(item => ({at:item.created_at, seq:0, title:`대화 · ${item.role || ''}`, body:item.text ?? item.content})),
  ...mergeEvents([], props.task.events || []).map(item => ({at:item.created_at, seq:item.seq, title:`진행 #${item.seq} · ${item.type}`, body:item.payload as unknown})),
  ...(props.task.reviews || []).map(item => ({at:item.created_at ?? item.reviewed_at, seq:0, title:`검토 · ${item.action}`, body:item as unknown}))
].sort((a, b) => {
  const delta = (Date.parse(a.at || '') || 0) - (Date.parse(b.at || '') || 0)
  return delta || a.seq - b.seq
}))

async function resume() {
  if (await investigation.activateTask(props.task.id)) router.push('/')
}
</script>

<template>
  <div class="detail-status">
    <div><p class="eyebrow">{{ task.legacyId || task.id }}</p><h3>{{ task.question }}</h3></div>
    <span class="approved-badge">{{ statuses[task.status] || task.status }}</span>
  </div>
  <div class="detail-meta">
    <div><span>요청자</span><strong>{{ task.user_name || '기존 로컬 기록' }} / {{ task.user_role || '미검증' }}</strong></div>
    <div><span>생성</span><strong>{{ date(task.created_at) }}</strong></div>
    <div><span>최근 갱신</span><strong>{{ date(task.updated_at) }}</strong></div>
  </div>
  <p v-if="task.legacy" class="data-notice">읽기 전용 로컬 기록 · 서버 검증 승인 아님</p>
  <div v-else class="record-cta">
    <button type="button" class="record-button" @click="resume">조사 열기 / 이어가기</button>
    <button v-if="task.report" type="button" class="record-button" @click="investigation.openReview(task)">조사 기록 만들기</button>
  </div>
  <ReportView v-if="task.report" :report="task.report" review />
  <h4>대화 · 진행 · 검토 시간순 이력</h4>
  <ol class="timeline">
    <li v-for="(item, index) in chronology" :key="index"><strong>{{ item.title }}</strong> · {{ date(item.at) }}<pre>{{ text(item.body) }}</pre></li>
    <li v-if="!chronology.length">이력이 없습니다.</li>
  </ol>
</template>
