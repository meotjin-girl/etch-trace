<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const investigation = useInvestigationStore()
const records = useRecordsStore()
const route = useRoute()
const content = ref<HTMLElement>()

// The panel follows the page in view: the selected record, otherwise the live task.
const docs = computed(() => (route.name === 'records' ? records.selected?.report : investigation.task?.report)?.documents || [])
const ariaHidden = computed(() => ui.evidenceClosed ? 'true' : ui.evidenceOpen ? 'false' : undefined)

watch(() => ui.highlight, async ({id}) => {
  if (!id) return
  await nextTick()
  const item = [...content.value?.querySelectorAll<HTMLElement>('[data-evidence-id]') || []]
    .find(element => element.dataset.evidenceId === id)
  item?.scrollIntoView({block:'nearest', behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'})
})
</script>

<template>
  <aside id="evidencePanel" class="evidence-panel" :class="{open: ui.evidenceOpen}" :aria-hidden="ariaHidden" aria-label="조사 근거">
    <div class="evidence-header">
      <div><p class="eyebrow">EVIDENCE</p><h2>조사 근거</h2></div>
      <button class="close-panel" type="button" aria-label="근거 패널 닫기" @click="ui.closeEvidence()"><i class="fi-rr-cross-small" aria-hidden="true"></i></button>
    </div>
    <div v-if="!docs.length" class="empty-evidence">
      <div class="empty-symbol" aria-hidden="true"><i class="fi-rr-search"></i></div>
      <strong>아직 연결된 근거가 없습니다</strong>
      <p>질문을 입력하면 관련 문서가 여기에 표시됩니다.</p>
    </div>
    <div v-else ref="content">
      <section class="evidence-group">
        <h3>관련 문서 <span>{{ docs.length }}건</span></h3>
        <article v-for="item in docs" :key="item.id" class="evidence-item" :class="{highlight: item.id === ui.highlight.id}" :data-evidence-id="item.id">
          <header><strong>{{ item.id }}</strong></header>
          <p class="report-text"><b>{{ item.title }}</b><br>{{ item.text }}</p>
        </article>
      </section>
    </div>
    <div class="data-notice">
      <strong>데모 데이터 안내</strong>
      <p>근거와 수치 분석은 서버 응답을 표시합니다. 데모 표시는 보고서의 demo 값에 따릅니다.</p>
    </div>
  </aside>
</template>
