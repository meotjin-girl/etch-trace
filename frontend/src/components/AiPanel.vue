<script setup lang="ts">
import TraceIcon from '@/components/TraceIcon.vue'
import { computed, nextTick, ref, watch } from 'vue'
import type { LiveInvestigation } from '@/api/live-models'
import { fixed, readingAt, sensorLabel, signed, type ParsedAlert } from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

const props = defineProps<{ investigation: LiveInvestigation, parsed: ParsedAlert }>()
const live = useLiveInvestigationsStore()
const tab = ref<'chat' | 'sensor' | 'docs'>('chat')
const chatBody = ref<HTMLElement | null>(null)
const suggestions = ['가장 유력한 원인은?', '추가로 확인할 센서는?', '관련 SOP 요약']
async function scrollToBottom() {
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}
watch([() => live.messages, () => live.busy, () => live.pending, tab], scrollToBottom, {deep:true, immediate:true})
function suggest(question: string) {
  if (!live.canSend) return
  live.draft = question
  void live.send()
}
const tabs = [{key:'chat', label:'대화', icon:'chat'}, {key:'sensor', label:'센서 분석', icon:'sensors'}, {key:'docs', label:'문서 근거', icon:'document'}] as const

// The first human message of an alert thread is the system alert text itself; show it collapsed.
const visibleMessages = computed(() => live.messages.filter(message => !message.text.startsWith('[경보]')))
const at = computed(() => props.parsed.alarms.find(item => item.source === 'equipment')?.time ?? props.parsed.alarms[0]?.time ?? '')
const rows = computed(() => props.parsed.sensors.map(series => {
  const reading = readingAt(props.parsed, series.sensor, at.value)
  const value = reading?.value ?? null
  const z = value !== null && series.mean !== null && series.sd ? (value - series.mean) / series.sd : null
  return {series, value, z}
}).sort((a, b) => Math.abs(b.z ?? 0) - Math.abs(a.z ?? 0)))
const docs = computed(() => [...new Set(props.investigation.candidates.flatMap(candidate => candidate.doc_ids))])
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void live.send()
  }
}
</script>

<template>
  <aside class="t-card ai-panel" aria-labelledby="aiHeading">
    <h2 id="aiHeading" class="t-icon-heading"><TraceIcon name="ai" />TRACE AI</h2>
    <div class="ai-tabs" role="tablist">
      <button v-for="item in tabs" :key="item.key" type="button" role="tab" :aria-selected="tab === item.key"
        @click="tab = item.key"><TraceIcon :name="item.icon" />{{ item.label }}</button>
    </div>

    <div v-if="tab === 'chat'" ref="chatBody" class="ai-body" data-testid="thread-conversation" aria-live="polite">
      <template v-for="(message, index) in visibleMessages" :key="message.id">
        <div v-if="message.role === 'user'" class="bubble user">
          <p>{{ message.text }}</p>
        </div>
        <div v-else class="ai-group">
          <span class="ai-avatar" aria-hidden="true"><TraceIcon name="ai" /></span>
          <div class="ai-content">
            <small v-if="visibleMessages[index - 1]?.role !== 'assistant'">TRACE AI</small>
            <div class="bubble ai"><p data-testid="thread-message">{{ message.text }}</p></div>
          </div>
        </div>
      </template>
      <div v-if="live.pending" class="bubble user"><p>{{ live.pending }}</p></div>
      <div v-if="!visibleMessages.length && !live.pending && !live.loading" class="chat-empty">
        <span class="empty-icon" aria-hidden="true"><TraceIcon name="ai" /></span>
        <p>경보 조사 결과에 대해 질문해 보세요.</p>
        <div class="suggestions">
          <button v-for="question in suggestions" :key="question" type="button" :disabled="!live.canSend"
            @click="suggest(question)">{{ question }}</button>
        </div>
      </div>
      <div v-if="live.busy" class="ai-group" role="status" aria-label="TRACE AI가 답변을 작성하는 중">
        <span class="ai-avatar" aria-hidden="true"><TraceIcon name="ai" /></span>
        <div class="bubble ai typing" aria-hidden="true"><span></span><span></span><span></span></div>
      </div>
    </div>

    <div v-else-if="tab === 'sensor'" class="ai-body">
      <p class="t-faint">{{ at }} 기준 · 정상 평균 대비 편차(σ) 큰 순서</p>
      <table class="sensor-table">
        <tbody>
          <tr v-for="row in rows" :key="row.series.sensor" :class="{hot: row.z !== null && Math.abs(row.z) > 3}">
            <th>{{ sensorLabel(row.series.sensor) }}</th>
            <td class="t-mono">{{ fixed(row.value) }} {{ row.series.unit }}</td>
            <td class="t-mono t-faint">{{ row.z === null ? '-' : `${signed(row.z, 1)}σ` }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="ai-body">
      <p v-if="!docs.length" class="t-faint">후보에 연결된 문서가 없습니다.</p>
      <RouterLink v-for="doc in docs" :key="doc" class="t-inner doc-link"
        :to="{path:`/sop/${encodeURIComponent(doc.split('#')[0]!)}`, query:{related:docs.join(','), from:investigation.id}}">
        <span class="t-link"><TraceIcon name="document" /> {{ doc }} <TraceIcon name="chevron" /></span>
      </RouterLink>
    </div>

    <div v-if="tab === 'chat'" class="chat-composer">
      <p v-if="live.error" class="chat-error" role="alert">{{ live.error }}</p>
      <form class="composer-row" data-testid="thread-composer" @submit.prevent="live.send()">
        <label class="sr-only" for="threadQuestion">TRACE AI에게 질문</label>
        <textarea id="threadQuestion" v-model="live.draft" rows="1" :disabled="!live.canSend"
          placeholder="알람·센서·문서에 대해 질문…" aria-describedby="composerHint" @keydown="keydown"></textarea>
        <button type="submit" class="send" aria-label="전송" :disabled="!live.canSend || !live.draft.trim()"><TraceIcon name="up" /></button>
      </form>
      <p id="composerHint" class="composer-hint">Enter 전송 · Shift+Enter 줄바꿈</p>
    </div>
  </aside>
</template>

<style scoped>
.ai-panel { display: flex; flex-direction: column; gap: 16px; min-height: 0; }
@media (max-width: 1080px) { .ai-panel { min-height: 480px; max-height: 80vh; } }
.ai-tabs { display: grid; grid-template-columns: repeat(3, 1fr); padding: 3px 10px; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface-2); }
.ai-tabs button { display: inline-flex; align-items: center; justify-content: center; gap: 5px; padding: 9px 0; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--text-muted); font-size: 12px; }
.ai-tabs button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); font-weight: 700; }
.ai-body { flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 0; overflow-y: auto; }
.bubble { padding: 11px 14px; border-radius: 14px 14px 14px 4px; font-size: 12px; line-height: 1.7; min-width: 0; flex-shrink: 0; }
.bubble p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.bubble.user { align-self: flex-end; max-width: 85%; border-radius: 14px 14px 4px 14px; background: var(--bubble); color: var(--bubble-text); }
.ai-group { display: flex; align-items: flex-start; gap: 8px; max-width: 85%; flex-shrink: 0; }
.ai-avatar { display: grid; place-items: center; flex: 0 0 24px; height: 24px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); }
.ai-content { min-width: 0; }
.ai-content small { display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 10px; }
.bubble.ai { border: 1px solid var(--border); background: var(--surface-2); }
.typing { display: flex; gap: 5px; align-items: center; min-height: 40px; }
.typing span { width: 5px; height: 5px; border-radius: 50%; background: var(--text-muted); animation: pulse 1.2s infinite ease-in-out; }
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }
@keyframes pulse { 0%, 60%, 100% { opacity: .35; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-3px); } }
@media (prefers-reduced-motion: reduce) { .typing span { animation: none; } }
.chat-empty { margin: auto 0; text-align: center; color: var(--text-muted); font-size: 12px; }
.empty-icon { color: var(--accent); font-size: 28px; }
.suggestions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.suggestions button { padding: 8px 10px; border: 1px solid var(--border); border-radius: 20px; color: var(--accent); background: var(--surface-2); font-size: 11px; }
.sensor-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sensor-table th, .sensor-table td { padding: 8px 4px; border-bottom: 1px solid var(--border); text-align: left; }
.sensor-table td { text-align: right; }
.sensor-table tr.hot th, .sensor-table tr.hot td:nth-child(2) { color: var(--danger); }
.doc-link { display: block; text-decoration: none; }
.chat-composer { flex-shrink: 0; }
.composer-row { display: flex; align-items: flex-end; gap: 9px; padding: 7px 7px 7px 15px; border: 1px solid var(--border); border-radius: 24px; background: var(--surface-2); }
.composer-row:focus-within { border-color: var(--accent); }
.composer-row textarea { field-sizing: content; flex: 1; min-width: 0; min-height: 22px; max-height: 88px; margin: 7px 0; line-height: 22px; padding: 0; border: 0; outline: 0; resize: none; background: transparent; color: var(--text); font: inherit; font-size: 12px; overflow-y: auto; }
.send { display: grid; place-items: center; flex: 0 0 36px; height: 36px; border: 0; border-radius: 50%; background: var(--bubble); color: var(--bubble-text); font-size: 20px; cursor: pointer; }
.send:disabled { opacity: .4; cursor: default; }
.composer-hint { margin: 7px 0 0; text-align: center; color: var(--text-muted); font-size: 10px; }
.chat-error { margin: 0 0 8px; color: var(--danger); font-size: 12px; overflow-wrap: anywhere; }
</style>
