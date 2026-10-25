<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StepBar from '@/components/StepBar.vue'
import { useInvestigation } from '@/composables/useInvestigation'
import { fixed, readingAt, sensorLabel, signed } from '@/lib/alert-text'

const {live, detail, parsed, head} = useInvestigation()
const route = useRoute()
const router = useRouter()
const candidateId = computed(() => String(route.params.cid ?? ''))
const index = computed(() => detail.value?.candidates.findIndex(item => item.id === candidateId.value) ?? -1)
const candidate = computed(() => detail.value?.candidates[index.value] ?? null)
const label = computed(() => `후보 ${String(index.value + 1).padStart(2, '0')}`)

// Sensors named by the alarms first, then the largest deviations, at most four rows.
const rows = computed(() => {
  if (!parsed.value || !head.value) return []
  const at = head.value.alarm.time
  const named = parsed.value.alarms.flatMap(alarm => alarm.sensor ? [alarm.sensor] : [])
  const ranked = parsed.value.sensors.map(series => {
    const reading = readingAt(parsed.value!, series.sensor, at)
    // The alarm's own sensor shows the reading the alarm reported, not the nearest 5-second sample.
    const value = head.value!.alarm.sensor === series.sensor && head.value!.value !== null ? head.value!.value : reading?.value ?? null
    const z = value !== null && series.mean !== null && series.sd ? (value - series.mean) / series.sd : 0
    return {series, value, first:reading?.first ?? null, z}
  }).sort((a, b) => Number(named.includes(b.series.sensor)) - Number(named.includes(a.series.sensor)) || Math.abs(b.z) - Math.abs(a.z))
  return ranked.slice(0, 4)
})
const approved = computed(() => detail.value?.approval ?? null)
async function choose() {
  if (!candidate.value) return
  if (await live.approve(candidate.value.id)) await router.push(`/investigations/${encodeURIComponent(detail.value!.id)}/action`)
}
const docLink = (doc: string) => `/sop/${encodeURIComponent(doc.split('#')[0]!)}`
</script>

<template>
  <PageHeader title="원인 후보 상세 분석">
    <template #subtitle>
      {{ detail?.alert.tool_id }}/{{ detail?.alert.chamber_id }} / {{ label }} · 실측과 문서의 일치·부족 항목을 확인합니다
    </template>
  </PageHeader>
  <StepBar :current="3" />
  <div v-if="live.error" class="t-notice" role="alert">{{ live.error }}</div>
  <p v-if="!detail" class="t-empty" role="status">조사를 불러오는 중…</p>
  <p v-else-if="!candidate" class="t-empty">이 후보는 현재 조사에 없습니다. 후보가 갱신됐을 수 있습니다.
    <RouterLink class="t-link" :to="`/investigations/${encodeURIComponent(detail.id)}`">제안서로 돌아가기</RouterLink></p>
  <template v-else>
    <section class="t-card summary">
      <header><span class="t-chip">{{ label }}</span><h2>{{ candidate.cause }}</h2></header>
      <p class="t-accent strong">분석 요약</p>
      <p class="body">{{ candidate.rationale }}</p>
      <p class="t-faint">권고 조치 · {{ candidate.action }}</p>
    </section>

    <div class="t-grid-2 evidence">
      <section class="t-card">
        <h3>01&nbsp; 센서 데이터</h3>
        <p class="t-sub">{{ head?.alarm.time }} · {{ detail.alert.tool_id }} / {{ detail.alert.chamber_id }}</p>
        <hr class="t-rule">
        <dl class="readings">
          <template v-for="row in rows" :key="row.series.sensor">
            <dt>{{ sensorLabel(row.series.sensor) }}
              <small>정상 {{ fixed(row.series.mean, 2) }} · {{ row.value !== null && row.series.mean !== null ? signed(row.value - row.series.mean) : '-' }}</small>
            </dt>
            <dd class="t-mono" :class="{['t-danger']: Math.abs(row.z) > 3}">{{ fixed(row.value) }} {{ row.series.unit }}
              <small v-if="row.first !== null">초기 {{ fixed(row.first) }}</small>
            </dd>
          </template>
        </dl>
        <p class="t-faint source">출처: 경보 센서 구간(5초) · 합성</p>
      </section>

      <section class="t-card">
        <h3>02&nbsp; 문서 근거</h3>
        <p class="docs">
          <RouterLink v-for="doc in candidate.doc_ids" :key="doc" class="t-link" :to="docLink(doc)">{{ doc }} ↗</RouterLink>
          <span v-if="!candidate.doc_ids.length" class="t-faint">연결된 문서 없음</span>
        </p>
        <hr class="t-rule">
        <div class="t-inner">
          <p v-for="check in candidate.checks" :key="check" class="check">{{ check }}</p>
          <p v-if="!candidate.checks.length" class="t-faint">확인 항목 미제공</p>
        </div>
        <p v-for="unknown in candidate.unknowns" :key="unknown" class="t-sub">{{ unknown }}</p>
        <p class="t-faint">문서 연결은 매핑 제안이며 재검증 전입니다.</p>
      </section>
    </div>

    <div class="t-actions">
      <RouterLink v-if="approved" class="t-btn" :to="`/investigations/${encodeURIComponent(detail.id)}/action`">
        {{ approved.candidate.id === candidate.id ? '선택한 원인' : '이미 다른 원인 선택됨' }} · 조치 검토 →
      </RouterLink>
      <button v-else type="button" class="t-btn" :data-approve-candidate="candidate.id" :disabled="live.approving || live.busy || live.loading"
        @click="choose">원인 선택 →</button>
    </div>
  </template>
</template>

<style scoped>
.summary header { display: flex; align-items: center; gap: 20px; }
.summary h2 { font-size: 27px; }
.strong { margin: 22px 0 8px; font-weight: 800; }
.body { margin: 0 0 12px; font-size: 17px; line-height: 1.8; white-space: pre-wrap; }
.evidence { margin-top: 26px; }
.readings { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 30px 20px; margin: 0; }
.readings dt { font-size: 17px; font-weight: 800; }
.readings dd { margin: 0; font-size: 18px; font-weight: 800; }
.readings small { display: block; margin-top: 10px; color: var(--text-muted); font-size: 14px; font-weight: 400; }
.source { margin-top: 30px; }
.docs { display: flex; flex-wrap: wrap; gap: 14px; margin: 12px 0 0; }
.check { margin: 0 0 10px; font-size: 16px; line-height: 1.7; }
</style>
