<script setup lang="ts">
import { computed } from 'vue'
import AiPanel from '@/components/AiPanel.vue'
import AlarmHeader from '@/components/AlarmHeader.vue'
import PageHeader from '@/components/PageHeader.vue'
import StepBar from '@/components/StepBar.vue'
import { useInvestigation } from '@/composables/useInvestigation'
import { ruleTitle } from '@/lib/alert-text'

const {live, detail, parsed, head} = useInvestigation()
const title = computed(() => head.value ? ruleTitle(head.value.alarm.rule) : '이상 조사')
const chosen = computed(() => detail.value?.approval?.candidate.id ?? null)
const number = (index: number) => String(index + 1).padStart(2, '0')
const docLink = (doc: string) => `/sop/${encodeURIComponent(doc.split('#')[0]!)}`
</script>

<template>
  <PageHeader :title="`${title} · 조사 제안서`">
    <template #subtitle>
      <RouterLink to="/" class="crumb">이상 로그</RouterLink> / {{ detail?.alert.tool_id }} · {{ detail?.alert.chamber_id }} / {{ title }}
    </template>
  </PageHeader>
  <StepBar :current="2" />
  <div v-if="live.error" class="t-notice" role="alert">{{ live.error }}</div>
  <p v-if="!detail" class="t-empty" role="status">조사를 불러오는 중…</p>
  <template v-else-if="parsed">
    <AlarmHeader :investigation="detail" :head="head" />
    <div class="t-split">
      <div class="t-stack" data-testid="current-candidates">
        <div class="t-card warning">
          <strong class="t-danger">선제 확인 · 조치 지시 아님</strong>
          <p class="t-sub">Hold 여부는 SOP-ETCH-20과 현장 권한으로 판단합니다. 원인은 확인 전 가설입니다.</p>
        </div>
        <h2 class="section-title">우선 후보와 추가 점검 항목</h2>
        <p v-if="!detail.candidates.length" class="t-empty">아직 원인 후보가 없습니다. TRACE AI 조사가 진행 중일 수 있습니다.</p>
        <article v-for="(candidate, index) in detail.candidates" :key="candidate.id" class="t-card candidate"
          :data-candidate-id="candidate.id">
          <header>
            <span class="t-chip">{{ chosen === candidate.id ? '선택됨' : number(index) }}</span>
            <h3>{{ candidate.cause }}</h3>
          </header>
          <p class="t-sub">{{ candidate.rationale }}</p>
          <footer>
            <RouterLink v-if="candidate.doc_ids[0]" class="t-link" :to="docLink(candidate.doc_ids[0])">{{ candidate.doc_ids[0] }} ↗</RouterLink>
            <span v-else></span>
            <RouterLink class="t-link" :to="`/investigations/${encodeURIComponent(detail.id)}/candidates/${encodeURIComponent(candidate.id)}`">
              분석 근거 보기 →
            </RouterLink>
          </footer>
        </article>
      </div>
      <AiPanel :investigation="detail" :parsed="parsed" />
    </div>
  </template>
</template>

<style scoped>
.crumb { color: inherit; text-decoration: none; }
.crumb:hover { text-decoration: underline; }
.warning strong { font-size: 18px; }
.section-title { margin: 12px 0 0; font-size: 24px; font-weight: 800; }
.candidate header { display: flex; align-items: center; gap: 18px; }
.candidate footer { display: flex; justify-content: space-between; gap: 16px; margin-top: 22px; }
</style>
