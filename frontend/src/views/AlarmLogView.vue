<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import type { InvestigationSummary } from '@/api/live-models'
import {
  fixed, headline, parseAlert, ruleTitle, sensorLabel, signed, stageLabels, stageOf, type Stage,
} from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'
import { useUiStore } from '@/stores/ui'

const PAGE = 20
const live = useLiveInvestigationsStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()
const tab = ref<Stage>('detected')
const shown = ref(PAGE)
onMounted(() => { void live.refreshList() })

const preview = (id: string) => {
  const item = live.previews[id]
  if (!item) return null
  const parsed = parseAlert(item.alert.source_text)
  return {item, parsed, head:headline(parsed)}
}
// The sidebar search matches tool, chamber, lot, summary and (once loaded) the alarm rules.
const matches = (item: InvestigationSummary) => {
  const term = ui.search.trim().toLocaleLowerCase()
  if (!term) return true
  const rules = preview(item.id)?.parsed.alarms.map(alarm => `${alarm.rule} ${ruleTitle(alarm.rule)}`) ?? []
  return [item.tool_id, item.chamber_id, item.lot_id, item.summary, ...rules].join(' ').toLocaleLowerCase().includes(term)
}
const filtered = computed(() => live.records.filter(matches))
const counts = computed(() => {
  const result: Record<Stage, number> = {detected:0, acting:0, done:0}
  filtered.value.forEach(item => { result[stageOf(item)] += 1 })
  return result
})
const inTab = computed(() => filtered.value.filter(item => stageOf(item) === tab.value))
const visible = computed(() => inTab.value.slice(0, shown.value))
watch(visible, items => { void live.loadPreviews(items.map(item => item.id)) }, {immediate:true})
watch(tab, () => { shown.value = PAGE })

const selectedId = computed(() => {
  const wanted = typeof route.query.id === 'string' ? route.query.id : ''
  return inTab.value.some(item => item.id === wanted) ? wanted : inTab.value[0]?.id ?? ''
})
const selected = computed(() => live.records.find(item => item.id === selectedId.value) ?? null)
const selectedPreview = computed(() => selected.value ? preview(selected.value.id) : null)
function select(id: string) { void router.replace({query:{...route.query, id}}) }

const shortLot = (lot: string) => lot.length > 14 ? `${lot.slice(0, 7)}…${lot.slice(-6)}` : lot
const clock = (iso: string) => new Date(iso).toLocaleTimeString('ko-KR', {hour12:false, timeZone:'Asia/Seoul'})
const occurred = (id: string, fallback: string) => {
  const found = preview(id)
  return found?.head?.alarm.time ?? clock(fallback)
}
</script>

<template>
  <PageHeader :step="1" title="이상 로그" subtitle="ETCH 장비의 합성 알람 · 경보가 들어오면 AI 조사가 자동으로 시작됩니다" />

  <div class="t-tabs" role="tablist" aria-label="처리 상태">
    <button v-for="stage in (['detected', 'acting', 'done'] as const)" :key="stage" type="button" role="tab"
      :class="stage" :aria-selected="tab === stage" @click="tab = stage">
      {{ stageLabels[stage] }}&nbsp; {{ counts[stage] || '–' }}{{ counts[stage] ? '건' : '' }}
    </button>
  </div>

  <div v-if="live.listError" class="t-notice" role="alert">
    {{ live.listError }}
    <button type="button" :disabled="live.loadingList" @click="live.refreshList()">다시 연결</button>
  </div>

  <div class="t-split t-fill t-cols">
    <section class="t-card" aria-labelledby="alarmListHeading" :aria-busy="live.loadingList">
      <h2 id="alarmListHeading">▦ 장비 알람 이벤트</h2>
      <p class="t-sub">Prometheus 경보 · 장비 알람과 FDC 경보를 Lot 단위로 묶음 · {{ inTab.length }}건</p>
      <hr class="t-rule">
      <p v-if="live.loadingList && !live.records.length" class="t-empty" role="status">알람을 불러오는 중…</p>
      <p v-else-if="!inTab.length" class="t-empty">{{ stageLabels[tab] }} 상태의 알람이 없습니다.</p>
      <div class="alarm-list">
        <button v-for="item in visible" :key="item.id" type="button" class="alarm-card"
          :class="{selected: item.id === selectedId}" :data-investigation-id="item.id"
          :aria-pressed="item.id === selectedId" @click="select(item.id)">
          <header>
            <span class="t-bang" aria-hidden="true">!</span>
            <strong>{{ item.tool_id }} / {{ item.chamber_id }}</strong>
            <span class="t-pill" :class="stageOf(item)">{{ stageLabels[stageOf(item)] }}</span>
          </header>
          <template v-if="preview(item.id)?.head">
            <h3>{{ ruleTitle(preview(item.id)!.head!.alarm.rule) }} · {{ preview(item.id)!.head!.alarm.rule }}</h3>
            <p class="t-mono">
              {{ fixed(preview(item.id)!.head!.value) }} {{ preview(item.id)!.head!.unit }}
              <template v-if="preview(item.id)!.head!.mean !== null"> / 정상 {{ fixed(preview(item.id)!.head!.mean, 2) }}</template>
              · {{ shortLot(item.lot_id) }} · {{ occurred(item.id, item.created_at) }}
            </p>
          </template>
          <template v-else>
            <h3>{{ item.summary }}</h3>
            <p>{{ shortLot(item.lot_id) }} · {{ clock(item.created_at) }}</p>
          </template>
        </button>
      </div>
      <button v-if="inTab.length > shown" type="button" class="t-btn block more" @click="shown += PAGE">
        더 보기 ({{ inTab.length - shown }}건)
      </button>
    </section>

    <aside class="t-card t-stack" aria-labelledby="selectedHeading">
      <h2 id="selectedHeading">◉ 현재 선택한 알람</h2>
      <p v-if="!selected" class="t-empty">목록에서 알람을 선택해 주세요.</p>
      <template v-else>
        <div class="t-inner picked">
          <header><span class="t-danger">{{ selected.tool_id }} · {{ selected.chamber_id }}</span></header>
          <div class="picked-title">
            <h3>{{ selectedPreview?.head ? ruleTitle(selectedPreview.head.alarm.rule) : selected.summary }}</h3>
            <span class="t-bang" aria-hidden="true">!</span>
          </div>
          <p v-if="selectedPreview?.head" class="t-faint">
            {{ selectedPreview.head.alarm.rule }} · {{ selectedPreview.head.alarm.source === 'equipment' ? '장비 알람' : 'FDC 경보' }}
          </p>
        </div>
        <div v-if="selectedPreview?.head" class="t-inner">
          <p class="t-faint strong">측정 {{ sensorLabel(selectedPreview.head.alarm.sensor) }}</p>
          <p class="big"><span class="t-danger t-mono">{{ fixed(selectedPreview.head.value) }}</span> <b>{{ selectedPreview.head.unit }}</b></p>
          <p class="t-faint t-mono">
            정상 {{ fixed(selectedPreview.head.mean) }}<template v-if="selectedPreview.head.deviation !== null"> · 편차 {{ signed(selectedPreview.head.deviation) }}</template>
          </p>
        </div>
        <div class="t-inner">
          <h3 class="small">▤ 이벤트 정보</h3>
          <hr class="t-rule">
          <dl class="t-kv">
            <dt>LOT</dt><dd>{{ selected.lot_id }}</dd>
            <dt>발생</dt><dd>{{ selectedPreview?.parsed.window?.date ?? '' }} {{ occurred(selected.id, selected.created_at) }} KST</dd>
            <dt>경보</dt><dd>{{ selectedPreview?.parsed.alarms.length ?? '–' }}건 · 후보 {{ selected.candidate_count }}개</dd>
            <dt>수신</dt><dd>Prometheus 합성 경보</dd>
          </dl>
        </div>
        <RouterLink class="t-btn block" :to="`/investigations/${encodeURIComponent(selected.id)}`" data-testid="open-investigation">
          조사하기
        </RouterLink>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.alarm-list { display: grid; gap: 16px; }
.alarm-card { display: block; width: 100%; padding: 16px 18px; border: 1px solid var(--border); border-radius: 9px; background: var(--surface-2); color: var(--text); text-align: left; }
.alarm-card:hover { border-color: var(--border-strong); }
.alarm-card.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.alarm-card header { display: flex; align-items: center; gap: 10px; }
.alarm-card header strong { font-size: 14px; }
.alarm-card header .t-pill { margin-left: auto; }
.alarm-card h3 { margin: 14px 0 10px; font-size: 16px; font-weight: 800; overflow-wrap: anywhere; }
.alarm-card p { margin: 0; color: var(--text-muted); font-size: 12px; }
.more { margin-top: 16px; }
.picked { border-left: 2px solid var(--danger); }
.picked header { font-size: 12px; font-weight: 800; text-align: right; }
.picked-title { display: flex; align-items: center; justify-content: space-between; margin: 8px 0; }
.picked-title h3 { font-size: 20px; }
.big { margin: 9px 0 8px; font-size: 30px; font-weight: 800; }
.big b { margin-left: 14px; font-size: 14px; }
.strong { font-weight: 800; color: var(--text-muted); }
.small { font-size: 13px; }
</style>
