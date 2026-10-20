<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, fmtTime, STATUS } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const ov = ref(null)
const tasks = ref([])
const error = ref('')
let timer
async function load() {
  try { [ov.value, tasks.value] = await Promise.all([api.overview(), api.tasks()]) } catch (e) { error.value = e.message }
}
const count = (s) => ov.value?.status.find((x) => x.status === s)?.n || 0
const total = computed(() => ov.value?.status.reduce((a, x) => a + x.n, 0) || 0)
onMounted(() => { load(); timer = setInterval(load, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <h1>운영 현황</h1>
  <p class="muted">조사 이력, 승인된 기록, 색인 문서, Agent 도구 호출 지표를 봅니다.</p>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-if="ov">
    <div class="kpis">
      <div class="panel kpi"><span class="muted">전체 조사</span><b>{{ total }}</b></div>
      <div v-for="(v, k) in STATUS" :key="k" class="panel kpi"><span class="muted">{{ v.label }}</span><b :class="`tone-${v.tone} pill`">{{ count(k) }}</b></div>
    </div>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); margin-top:16px">
      <div class="panel">
        <h2>Agent 도구 호출</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>도구</th><th class="num">호출</th><th class="num">평균 ms</th><th class="num">오류</th></tr></thead>
          <tbody><tr v-for="t in ov.tool_calls" :key="t.name"><td class="mono">{{ t.name }}</td><td class="num">{{ t.calls }}</td><td class="num">{{ t.avg_ms }}</td><td class="num">{{ t.errors }}</td></tr></tbody>
        </table></div>
      </div>
      <div class="panel">
        <h2>데이터 · 지식 색인</h2>
        <table>
          <thead><tr><th>장비</th><th class="num">run</th><th class="num">고장 기록</th></tr></thead>
          <tbody><tr v-for="d in ov.data" :key="d.tool"><td class="mono">{{ d.tool }}</td><td class="num">{{ d.runs.toLocaleString() }}</td><td class="num">{{ d.faults }}</td></tr></tbody>
        </table>
        <table style="margin-top:12px">
          <thead><tr><th>문서</th><th class="num">chunk</th><th>임베딩 모델</th></tr></thead>
          <tbody><tr v-for="d in ov.docs" :key="d.source"><td class="mono">{{ d.source }}</td><td class="num">{{ d.chunks }}</td><td class="mono">{{ d.embed_model }}</td></tr></tbody>
        </table>
      </div>
    </div>
    <div class="panel" style="margin-top:16px">
      <h2>승인된 조사 기록</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>대상</th><th>요약</th><th>승인</th></tr></thead>
        <tbody>
          <tr v-for="i in ov.investigations" :key="i.id"><td class="mono">INV-{{ String(i.id).padStart(4, '0') }}</td><td class="mono">{{ i.tool }} · {{ i.run_id }}</td><td>{{ i.summary }}</td><td>{{ i.approved_by }}<br /><span class="muted">{{ fmtTime(i.approved_at) }}</span></td></tr>
          <tr v-if="!ov.investigations.length"><td colspan="4" class="muted">아직 없습니다.</td></tr>
        </tbody>
      </table></div>
    </div>
    <div class="panel" style="margin-top:16px">
      <h2>전체 조사 이력</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>상태</th><th>대상</th><th>요청자</th><th>요청</th><th>시각</th></tr></thead>
        <tbody><tr v-for="t in tasks" :key="t.id">
          <td><StatusBadge :status="t.status" /></td><td class="mono">{{ t.tool }} · {{ t.run_id }}</td>
          <td>{{ t.user_name }}</td><td>{{ t.question }}<div v-if="t.error" class="error">{{ t.error }}</div></td><td class="mono">{{ fmtTime(t.created_at) }}</td>
        </tr></tbody>
      </table></div>
    </div>
  </template>
</template>
<style scoped>
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; }
.kpi { display: flex; flex-direction: column; gap: 4px; } .kpi b { font-size: 26px; font-variant-numeric: tabular-nums; }
.pill { background: none !important; }
</style>
