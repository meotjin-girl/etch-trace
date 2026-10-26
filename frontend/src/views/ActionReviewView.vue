<script setup lang="ts">
import { computed } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StepBar from '@/components/StepBar.vue'
import { useInvestigation } from '@/composables/useInvestigation'

const {live, detail} = useInvestigation()
const chosen = computed(() => detail.value?.approval?.candidate ?? null)
const items = computed(() => [
  ...(chosen.value?.checks ?? []).map(title => ({title, note:'현장에서 확인 후 결과를 기록합니다'})),
  {title:'실제 조치와 결과는 별도 입력', note:'원인 선택만으로 조치 완료 처리하지 않음'},
])
</script>

<template>
  <PageHeader title="원인 선택 · 조치 검토">
    <template #subtitle>{{ detail?.alert.tool_id }}/{{ detail?.alert.chamber_id }} / 선택한 원인의 확인 항목을 검토합니다</template>
  </PageHeader>
  <StepBar :current="4" />
  <div v-if="live.error" class="t-notice" role="alert">{{ live.error }}</div>
  <p v-if="!detail" class="t-empty" role="status">조사를 불러오는 중…</p>
  <p v-else-if="!chosen" class="t-empty">아직 원인이 선택되지 않았습니다.
    <RouterLink class="t-link" :to="`/investigations/${encodeURIComponent(detail.id)}`">제안서에서 후보 선택하기</RouterLink></p>
  <template v-else>
    <section class="t-card chosen" data-testid="approved-snapshot">
      <header><span class="t-chip">선택됨</span><h2>{{ chosen.cause }}</h2></header>
      <p class="t-sub">근거 · {{ chosen.rationale }}</p>
      <p class="t-faint">{{ detail.approval!.approved_by }} 선택 · {{ new Date(detail.approval!.approved_at).toLocaleString('ko-KR') }}</p>
    </section>

    <h2 class="section-title">문서가 요구하는 현장 확인</h2>
    <p class="t-sub">{{ chosen.doc_ids.join(', ') || '연결 문서 없음' }} 확인 항목 · 자동 장비 제어 없음</p>
    <ol class="checks">
      <li v-for="(item, index) in items" :key="item.title" class="t-card">
        <span class="t-chip">{{ String(index + 1).padStart(2, '0') }}</span>
        <div><strong>{{ item.title }}</strong><p class="t-sub">{{ item.note }}</p></div>
      </li>
    </ol>
    <div class="t-actions">
      <RouterLink class="t-btn" :to="`/investigations/${encodeURIComponent(detail.id)}/record`">
        {{ detail.action ? '기록 보기' : '수행한 조치 기록하기' }} →
      </RouterLink>
    </div>
  </template>
</template>

<style scoped>
.chosen header { display: flex; align-items: center; gap: 15px; }
.section-title { margin: 33px 0 0; font-size: 18px; font-weight: 800; }
.checks { display: grid; gap: 16px; margin: 20px 0 0; padding: 0; list-style: none; }
.checks li { display: flex; gap: 18px; align-items: flex-start; }
.checks strong { font-size: 15px; }
</style>
