<script setup lang="ts">
import type { LiveInvestigation } from '@/api/live-models'
import InvestigationCandidate from './InvestigationCandidate.vue'
import { date, shortId } from '@/lib/format'

defineProps<{ investigation: LiveInvestigation, blocked: boolean }>()
defineEmits<{ approve: [id: string] }>()
</script>

<template>
  <div class="detail-status">
    <div>
      <p class="eyebrow" :title="investigation.id">#{{ shortId(investigation.id) }} · 데모</p>
      <h2>{{ investigation.summary }}</h2>
    </div>
    <span class="approved-badge">{{ investigation.approval ? '승인됨' : '검토 대기' }}</span>
  </div>
  <div class="detail-meta">
    <div><span>장비 / 챔버</span><strong>{{ investigation.alert.tool_id }} / {{ investigation.alert.chamber_id }}</strong></div>
    <div><span>Lot / Wafer</span><strong>{{ investigation.alert.lot_id }} / {{ investigation.alert.wafer_id }}</strong></div>
    <div><span>레시피</span><strong>{{ investigation.alert.recipe_id }}</strong></div>
  </div>
  <details>
    <summary>원본 경보</summary>
    <p class="report-text">{{ investigation.alert.source_text }}</p>
  </details>
  <section data-testid="current-candidates" aria-labelledby="candidatesHeading">
    <h3 id="candidatesHeading">현재 원인 후보 · 버전 {{ investigation.revision }}</h3>
    <p>최근 갱신 {{ date(investigation.updated_at) }}</p>
    <InvestigationCandidate v-for="candidate in investigation.candidates" :key="candidate.id" :candidate="candidate">
      <button v-if="!investigation.approval" class="primary-button candidate-approve" type="button"
        :data-approve-candidate="candidate.id" :aria-label="`${candidate.cause} 후보 승인`"
        :disabled="blocked" @click="$emit('approve', candidate.id)">이 후보 승인</button>
    </InvestigationCandidate>
  </section>
  <section v-if="investigation.approval" data-testid="approved-snapshot" aria-labelledby="approvalHeading">
    <h3 id="approvalHeading">승인 당시 스냅샷 · 버전 {{ investigation.approval.revision }}</h3>
    <p>{{ investigation.approval.approved_by }} · {{ date(investigation.approval.approved_at) }}</p>
    <p>이후 대화로 현재 후보가 변경되어도 이 승인 내용은 유지됩니다.</p>
    <InvestigationCandidate :candidate="investigation.approval.candidate" />
    <p v-if="investigation.approval.comment" class="report-text">{{ investigation.approval.comment }}</p>
  </section>
</template>

<style scoped>
h2 { margin: 0; font-size: 19px; }
section { margin-top: 24px; }
h3 { font-size: 15px; }
p, summary { font-size: 14px; line-height: 1.65; }
.candidate-approve { margin-top: 12px; }
</style>
