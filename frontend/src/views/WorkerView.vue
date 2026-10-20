<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { api, fmtTime } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import ReportCard from '../components/ReportCard.vue'

const form = ref({ tool: '01M01', run_id: '', question: '' })
const suggestions = ref([])
const nearFaults = ref([])
const tasks = ref([])
const selected = ref(null)
const error = ref('')
const sending = ref(false)
let timer

async function refresh() {
  try {
    tasks.value = await api.tasks(true)
    if (selected.value) selected.value = await api.task(selected.value.id)
  } catch (e) { error.value = e.message }
}
watch(() => form.value.run_id, async (q) => {
  if (q.length >= 2) suggestions.value = await api.runs(q).catch(() => [])
})
function pick(f) {
  form.value.run_id = f.run_id
  form.value.question = `이 run 직후 '${f.fault_name}' 알람으로 장비가 정지했습니다. 같은 레시피의 이전 run과 비교해 조사해 주세요.`
}
async function submit() {
  error.value = ''
  sending.value = true
  try {
    const { taskId } = await api.createTask(form.value)
    form.value.question = ''
    await refresh()
    selected.value = await api.task(taskId)
  } catch (e) { error.value = e.message } finally { sending.value = false }
}
onMounted(async () => {
  nearFaults.value = await api.nearFaults().catch(() => [])
  refresh()
  timer = setInterval(refresh, 3000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <h1>이상 조사 요청</h1>
  <p class="muted">이상해 보이는 run을 알려주시면 Agent가 비교·근거 수집을 하고, 공정 엔지니어가 검토·승인합니다.</p>
  <div class="grid cols-2" style="margin-top:16px">
    <form class="panel" @submit.prevent="submit">
      <h2>새 요청</h2>
      <label for="tool">장비</label>
      <select id="tool" v-model="form.tool"><option value="01M01">01M01 (이온 밀 식각)</option></select>
      <label for="run">run_id <span class="muted">({runnum}-{Lot})</span></label>
      <input id="run" v-model="form.run_id" list="runs" placeholder="예: 10825571-1132" required />
      <datalist id="runs"><option v-for="r in suggestions" :key="r.run_id" :value="r.run_id">recipe {{ r.recipe }} · {{ r.minutes }}분</option></datalist>
      <label>시연용 — 고장 기록 직전 run</label>
      <div class="chips">
        <button v-for="f in nearFaults.slice(0, 8)" :key="f.run_id + f.fault_name" type="button" class="chip" :title="f.fault_name" @click="pick(f)">
          {{ f.run_id }} · {{ f.hours_before }}h 전
        </button>
      </div>
      <label for="q">증상 / 요청</label>
      <textarea id="q" v-model="form.question" required placeholder="어떤 점이 이상했는지 적어주세요"></textarea>
      <p v-if="error" class="error" style="margin-top:10px">{{ error }}</p>
      <button :disabled="sending" style="margin-top:12px;width:100%">{{ sending ? '접수 중…' : '조사 요청' }}</button>
    </form>

    <div class="grid">
      <div class="panel">
        <h2>내 요청</h2>
        <ul class="list">
          <li v-for="t in tasks" :key="t.id" :class="{ active: selected?.id === t.id }" @click="api.task(t.id).then((x) => (selected = x))">
            <div class="row spread"><span class="mono">{{ t.tool }} · {{ t.run_id }}</span><StatusBadge :status="t.status" /></div>
            <div class="muted">{{ t.question }}</div>
            <div class="muted mono" style="font-size:11px">{{ fmtTime(t.created_at) }}</div>
          </li>
          <li v-if="!tasks.length" class="muted">아직 요청이 없습니다.</li>
        </ul>
      </div>
      <div v-if="selected" class="panel">
        <div class="row spread"><h2>{{ selected.run_id }} 조사 결과</h2><StatusBadge :status="selected.status" /></div>
        <p v-if="selected.status === 'WAITING_APPROVAL'" class="notice">보고서 초안이 작성되어 공정 엔지니어 검토 중입니다.</p>
        <p v-if="selected.status === 'RUNNING' || selected.status === 'QUEUED'" class="muted">Agent가 조사 중입니다…</p>
        <p v-if="selected.status === 'FAILED'" class="error">{{ selected.error }}</p>
        <template v-if="selected.status === 'DONE'">
          <p v-if="selected.investigation_id" class="muted">승인: {{ selected.approved_by }} · {{ fmtTime(selected.approved_at) }} · INV-{{ String(selected.investigation_id).padStart(4, '0') }}</p>
          <ReportCard :report="selected.report" />
        </template>
      </div>
    </div>
  </div>
</template>
