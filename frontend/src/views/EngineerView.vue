<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, subscribe, fmtTime } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import ReportCard from '../components/ReportCard.vue'
import Timeline from '../components/Timeline.vue'
import EvidencePanel from '../components/EvidencePanel.vue'

const route = useRoute()
const router = useRouter()
const tasks = ref([])
const filter = ref('ALL')
const task = ref(null)
const events = ref([])
const comment = ref('')
const busy = ref(false)
const error = ref('')
let stop = () => {}
let timer

const shown = computed(() => tasks.value.filter((t) => filter.value === 'ALL' || t.status === filter.value))
const report = computed(() => [...events.value].reverse().find((e) => e.type === 'APPROVAL_REQUIRED' || e.type === 'DONE')?.report || task.value?.report)
const waiting = computed(() => events.value.at(-1)?.type === 'APPROVAL_REQUIRED')

async function loadList() { tasks.value = await api.tasks().catch(() => tasks.value) }
async function open(id) {
  stop()
  events.value = []
  error.value = ''
  task.value = id ? await api.task(id).catch((e) => ((error.value = e.message), null)) : null
  if (!task.value) return
  stop = subscribe(id, (e) => {
    events.value.push(e)
    if (['APPROVAL_REQUIRED', 'DONE', 'FAILED'].includes(e.type)) { loadList(); api.task(id).then((t) => (task.value = t)) }
  })
}
async function decide(action) {
  busy.value = true
  error.value = ''
  try {
    await api.approve(task.value.id, action, comment.value)
    comment.value = ''
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
watch(() => route.params.id, open)
onMounted(() => {
  loadList()
  open(route.params.id)
  timer = setInterval(loadList, 4000)
})
onUnmounted(() => { stop(); clearInterval(timer) })
</script>

<template>
  <h1>조사 검토</h1>
  <p class="muted">Agent의 조사 과정을 실시간으로 보고, 보고서를 승인하거나 수정을 요청합니다. 승인 전에는 아무것도 저장되지 않습니다.</p>
  <div class="grid cols-2" style="margin-top:16px">
    <aside class="panel">
      <div class="row spread"><h2>조사 목록</h2>
        <select v-model="filter" style="width:auto" aria-label="상태 필터">
          <option value="ALL">전체</option><option value="WAITING_APPROVAL">검토 대기</option>
          <option value="RUNNING">조사 중</option><option value="DONE">완료</option><option value="FAILED">실패</option>
        </select>
      </div>
      <ul class="list">
        <li v-for="t in shown" :key="t.id" :class="{ active: task?.id === t.id }" @click="router.push(`/engineer/${t.id}`)">
          <div class="row spread"><span class="mono">{{ t.tool }} · {{ t.run_id }}</span><StatusBadge :status="t.status" /></div>
          <div class="muted">{{ t.user_name }} · {{ fmtTime(t.created_at) }}</div>
        </li>
        <li v-if="!shown.length" class="muted">해당 조사가 없습니다.</li>
      </ul>
    </aside>

    <section v-if="task" class="grid">
      <div class="panel">
        <div class="row spread">
          <h2 class="mono">{{ task.tool }} · run {{ task.run_id }}</h2>
          <StatusBadge :status="task.status" />
        </div>
        <p>“{{ task.question }}” <span class="muted">— {{ task.user_name }}</span></p>
      </div>

      <div v-if="waiting" class="panel approval">
        <h2>검토 요청 — 이 보고서를 조사 기록으로 저장할까요?</h2>
        <label for="cm">수정 요청 내용 (수정 요청 시)</label>
        <textarea id="cm" v-model="comment" placeholder="예: z가 3 미만인 항목은 '경미한 편차'로 표현해 주세요"></textarea>
        <div class="row" style="margin-top:10px">
          <button :disabled="busy" @click="decide('approve')">승인하고 저장</button>
          <button class="warn" :disabled="busy || !comment.trim()" @click="decide('revise')">수정 요청</button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>

      <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))">
        <div class="panel"><h2>진행 (SSE)</h2><Timeline :events="events" /></div>
        <div class="panel"><h2>수집 근거</h2><EvidencePanel :events="events" /></div>
      </div>
      <div class="panel"><h2>조사 보고서 {{ waiting ? '초안' : '' }}</h2>
        <ReportCard v-if="report" :report="report" />
        <p v-else class="muted">보고서 작성 전입니다.</p>
      </div>
    </section>
    <section v-else class="panel muted">왼쪽에서 조사를 선택하세요.</section>
  </div>
</template>
<style scoped>
.approval { border-color: var(--warn); background: var(--warn-soft); }
.approval textarea { background: var(--panel); }
</style>
