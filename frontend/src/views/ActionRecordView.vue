<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StepBar from '@/components/StepBar.vue'
import { useInvestigation } from '@/composables/useInvestigation'
import { fixed, ruleTitle } from '@/lib/alert-text'

const {live, detail, head} = useInvestigation()
const router = useRouter()
const content = ref('')
const result = ref('')
const chosen = computed(() => detail.value?.approval?.candidate ?? null)
const ready = computed(() => content.value.trim() && result.value.trim() && !live.recording)
async function save() {
  if (!ready.value || !detail.value) return
  if (await live.recordAction(content.value.trim(), result.value.trim())) {
    await router.push(`/records/${encodeURIComponent(detail.value.id)}`)
  }
}
</script>

<template>
  <PageHeader title="조치 기록">
    <template #subtitle>{{ detail?.alert.tool_id }}/{{ detail?.alert.chamber_id }} / 현장에서 수행한 조치만 입력합니다</template>
  </PageHeader>
  <StepBar :current="5" />
  <div v-if="live.error" class="t-notice" role="alert">{{ live.error }}</div>
  <p v-if="!detail" class="t-empty" role="status">조사를 불러오는 중…</p>
  <p v-else-if="!chosen" class="t-empty">원인을 먼저 선택해야 조치를 기록할 수 있습니다.
    <RouterLink class="t-link" :to="`/investigations/${encodeURIComponent(detail.id)}`">제안서로 이동</RouterLink></p>
  <div v-else class="record-grid">
    <section class="t-card">
      <h2>알람 정보</h2>
      <p class="t-danger tool">{{ detail.alert.tool_id }} / {{ detail.alert.chamber_id }}</p>
      <template v-if="head">
        <p class="line">{{ ruleTitle(head.alarm.rule) }} {{ fixed(head.value) }} {{ head.unit }}</p>
        <p class="t-faint">정상 {{ fixed(head.mean, 2) }} {{ head.unit }} · {{ head.alarm.time }} KST</p>
      </template>
      <hr class="t-rule">
      <p class="t-faint">선택한 원인</p>
      <p class="cause">{{ chosen.cause }}</p>
      <RouterLink v-for="doc in chosen.doc_ids" :key="doc" class="t-link doc" :to="`/sop/${encodeURIComponent(doc.split('#')[0]!)}`">{{ doc }}</RouterLink>
      <hr class="t-rule">
      <p class="t-faint">원본 데이터에는 실제 조치·담당자·Hold 상태가 기록되지 않습니다.</p>
    </section>

    <section class="t-card">
      <h2>실제로 수행한 조치</h2>
      <p class="t-sub">행동과 확인 결과를 사실대로 입력하세요.</p>
      <template v-if="detail.action">
        <div class="t-field"><span>조치 내용</span><p class="t-inner saved">{{ detail.action.content }}</p></div>
        <div class="t-field"><span>확인 결과</span><p class="t-inner saved">{{ detail.action.result }}</p></div>
        <p class="t-faint">{{ detail.action.recorded_by }} · {{ new Date(detail.action.recorded_at).toLocaleString('ko-KR') }} 저장됨</p>
        <div class="t-actions"><RouterLink class="t-btn" :to="`/records/${encodeURIComponent(detail.id)}`">조사 기록 보기 →</RouterLink></div>
      </template>
      <form v-else data-testid="action-form" @submit.prevent="save">
        <label class="t-field"><span>조치 내용 *</span>
          <textarea v-model="content" rows="6" required maxlength="10000" placeholder="현장에서 실제 수행한 내용 입력"></textarea>
        </label>
        <label class="t-field"><span>확인 결과 *</span>
          <textarea v-model="result" rows="3" required maxlength="10000" placeholder="측정값·관찰 결과·미확인 항목 입력"></textarea>
        </label>
        <p class="t-sub">저장 후에만 조사 기록에 표시됩니다. 저장한 내용은 수정할 수 없습니다.</p>
        <div class="t-actions"><button type="submit" class="t-btn" :disabled="!ready">기록 저장 →</button></div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.record-grid { display: grid; grid-template-columns: minmax(0, 520px) minmax(0, 1fr); gap: 30px; align-items: start; }
.tool { margin: 28px 0 14px; font-size: 20px; font-weight: 800; }
.line { margin: 0 0 12px; font-size: 19px; }
.cause { margin: 10px 0 18px; font-size: 21px; font-weight: 800; }
.doc { display: block; margin-bottom: 6px; font-weight: 500; }
.saved { margin: 0; white-space: pre-wrap; font-size: 16px; line-height: 1.7; }
@media (max-width: 1080px) { .record-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
