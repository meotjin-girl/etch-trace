<script setup lang="ts">
import { computed } from 'vue'
import type { Report } from '@/api/types'
import { labels, number, text, units } from '@/lib/format'
import { useUiStore } from '@/stores/ui'

const props = defineProps<{ report: Report, review?: boolean }>()
defineEmits<{ review: [] }>()
const ui = useUiStore()

const heading = computed(() => {
  const context = props.report.context || {}
  return [context.equipment, context.chamber, context.recipe].filter(Boolean).join(' / ') || '조사'
})
</script>

<template>
  <p class="message-label">근거 기반 조사 결과{{ report.demo === true ? ' · 데모 데이터' : '' }}</p>
  <h2>{{ heading }} 분석 결과</h2>
  <p class="answer-summary report-text">{{ text(report.summary) }}</p>
  <div class="analysis-grid">
    <div v-for="(metric, index) in report.metrics" :key="index" class="metric-card">
      <header><strong>{{ labels[metric.key] || metric.key }}</strong><span class="severity">{{ metric.severity }}</span></header>
      <div class="metric-values"><b>{{ metric.value }}</b><span>{{ units[metric.key] || '' }} · 비교군 평균 {{ number(metric.mean) }}</span></div>
      <div class="delta">평균 대비 {{ number(metric.deltaPct) }}% · z-score {{ number(metric.z) }}</div>
    </div>
    <p v-if="!report.metrics?.length">계측값 미제공</p>
  </div>
  <section class="answer-section">
    <h3>우선 확인할 항목</h3>
    <div class="cause-list">
      <div v-for="(item, index) in report.causeCases" :key="index" class="cause-item">
        <span>{{ index + 1 }}</span>
        <div><strong>{{ item.cause }}</strong><small>{{ item.action }}</small></div>
        <span class="citation">[{{ item.id }}]</span>
        <div class="cause-docs">
          <button v-for="doc in item.docs" :key="doc" type="button" class="citation" @click="ui.openEvidence(doc)">[{{ doc }}]</button>
        </div>
      </div>
      <p v-if="!report.causeCases?.length">원인 후보를 좁힐 근거가 부족합니다.</p>
    </div>
  </section>
  <section class="answer-section">
    <h3>문서 근거</h3>
    <button v-for="doc in report.docIds" :key="doc" type="button" class="citation" @click="ui.openEvidence(doc)">[{{ doc }}]</button>
  </section>
  <div v-if="!review" class="record-cta">
    <p><strong>조사 결과를 기록으로 남길까요?</strong><br>서버 검토 상태와 권한을 확인해 승인 또는 수정을 요청합니다.</p>
    <button class="record-button" type="button" @click="$emit('review')">조사 기록 만들기</button>
  </div>
</template>
