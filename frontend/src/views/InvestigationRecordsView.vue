<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { fixed, headline, parseAlert, ruleTitle, stageOf } from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

const live = useLiveInvestigationsStore()
const route = useRoute()
const query = ref('')
onMounted(() => { void live.refreshList() })

const done = computed(() => live.records.filter(item => stageOf(item) === 'done'))
const filtered = computed(() => {
  const term = query.value.trim().toLocaleLowerCase()
  return done.value.filter(item => [item.tool_id, item.chamber_id, item.lot_id, item.summary]
    .join(' ').toLocaleLowerCase().includes(term))
})
const selectedId = computed(() => typeof route.params.id === 'string' ? route.params.id : '')
watch([selectedId, done], ([id]) => { if (id) void live.loadPreviews([id]) }, {immediate:true})
const record = computed(() => live.previews[selectedId.value] ?? null)
const head = computed(() => record.value ? headline(parseAlert(record.value.alert.source_text)) : null)
const when = (iso: string | null | undefined) => iso ? new Date(iso).toLocaleString('ko-KR') : '-'
</script>

<template>
  <PageHeader title="조사 기록" subtitle="저장된 조사 결과를 다시 확인하는 메뉴 · 조치 기록까지 마친 조사만 표시" ruled />
  <div v-if="live.listError" class="t-notice" role="alert">{{ live.listError }}
    <button type="button" @click="live.refreshList()">다시 연결</button></div>
  <div class="records t-fill t-cols">
    <section class="t-card" aria-labelledby="recordListHeading">
      <h2 id="recordListHeading">기록 목록</h2>
      <label class="t-search inline"><i class="fi-rr-search" aria-hidden="true"></i>
        <span class="sr-only">장비·알람 검색</span>
        <input v-model="query" type="search" placeholder="장비·알람 검색"></label>
      <hr class="t-rule">
      <p v-if="!filtered.length" class="empty-strong">{{ done.length ? '검색 결과 없음' : '저장된 조사 기록 없음' }}</p>
      <RouterLink v-for="item in filtered" :key="item.id" class="t-inner record-item" :class="{active: item.id === selectedId}"
        :to="`/records/${encodeURIComponent(item.id)}`" :data-record-id="item.id">
        <strong>{{ item.tool_id }} / {{ item.chamber_id }}</strong>
        <span>{{ item.summary }}</span>
        <small class="t-faint">조치 기록 {{ when(item.action_recorded_at) }}</small>
      </RouterLink>
    </section>

    <section class="t-card record-detail" aria-live="polite">
      <template v-if="record && record.action && record.approval">
        <h2>{{ record.approval.candidate.cause }}</h2>
        <p class="t-sub">{{ record.alert.tool_id }} / {{ record.alert.chamber_id }} · {{ record.alert.lot_id }}</p>
        <hr class="t-rule">
        <dl class="t-kv wide">
          <dt>알람</dt><dd>{{ head ? `${ruleTitle(head.alarm.rule)} · ${fixed(head.value)} ${head.unit} (${head.alarm.time} KST)` : record.summary }}</dd>
          <dt>선택 원인</dt><dd>{{ record.approval.candidate.cause }} · {{ record.approval.approved_by }} · {{ when(record.approval.approved_at) }}</dd>
          <dt>근거 문서</dt><dd>{{ record.approval.candidate.doc_ids.join(', ') || '-' }}</dd>
          <dt>조치 내용</dt><dd class="pre">{{ record.action.content }}</dd>
          <dt>확인 결과</dt><dd class="pre">{{ record.action.result }}</dd>
          <dt>기록</dt><dd>{{ record.action.recorded_by }} · {{ when(record.action.recorded_at) }}</dd>
        </dl>
      </template>
      <template v-else>
        <h2>{{ done.length ? '기록을 선택해 주세요' : '조사 기록이 아직 없습니다' }}</h2>
        <div class="t-actions bottom"><RouterLink class="t-btn" to="/">이상 로그로 이동 →</RouterLink></div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.records { display: grid; grid-template-columns: minmax(0, 420px) minmax(0, 1fr); gap: 24px; align-items: stretch; }
.inline { margin-top: 20px; }
.empty-strong { font-size: 14px; font-weight: 800; }
.record-item { display: grid; gap: 6px; margin-bottom: 10px; color: var(--text); text-decoration: none; }
.record-item.active { border-color: var(--accent); }
.record-detail { display: flex; flex-direction: column; }
.wide { grid-template-columns: 82px 1fr; font-size: 12px; }
.pre { white-space: pre-wrap; line-height: 1.7; }
.bottom { margin-top: auto; }
@media (max-width: 1080px) { .records { grid-template-columns: minmax(0, 1fr); } }
</style>
