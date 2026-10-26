<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LiveInvestigation } from '@/api/live-models'
import { fixed, readingAt, sensorLabel, signed, type ParsedAlert } from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

const props = defineProps<{ investigation: LiveInvestigation, parsed: ParsedAlert }>()
const live = useLiveInvestigationsStore()
const tab = ref<'chat' | 'sensor' | 'docs'>('chat')
const tabs = [{key:'chat', label:'대화'}, {key:'sensor', label:'센서 분석'}, {key:'docs', label:'문서 근거'}] as const

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
    <h2 id="aiHeading">✧ TRACE AI</h2>
    <div class="ai-tabs" role="tablist">
      <button v-for="item in tabs" :key="item.key" type="button" role="tab" :aria-selected="tab === item.key"
        @click="tab = item.key">{{ item.label }}</button>
    </div>

    <div v-if="tab === 'chat'" class="ai-body" data-testid="thread-conversation" aria-live="polite">
      <template v-for="message in visibleMessages" :key="message.id">
        <div v-if="message.role === 'user'" class="bubble user">
          <small>◉ 엔지니어 · 질문</small>
          <p>{{ message.text }}</p>
        </div>
        <div v-else class="bubble ai">
          <small class="t-accent">✧ TRACE AI · 데이터 분석</small>
          <p data-testid="thread-message">{{ message.text }}</p>
        </div>
      </template>
      <p v-if="!visibleMessages.length && !live.loading" class="t-faint">경보 조사 결과에 대해 질문해 보세요.</p>
      <p v-if="live.busy" class="t-faint" role="status">TRACE AI가 답변을 작성하는 중…</p>
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
        <span class="t-link">{{ doc }} ↗</span>
      </RouterLink>
    </div>

    <form v-if="tab === 'chat'" class="composer-row" data-testid="thread-composer" @submit.prevent="live.send()">
      <label class="sr-only" for="threadQuestion">TRACE AI에게 질문</label>
      <textarea id="threadQuestion" v-model="live.draft" rows="1" :disabled="!live.canSend"
        placeholder="알람·센서·문서에 대해 질문…" @keydown="keydown"></textarea>
      <button type="submit" class="t-btn send" :disabled="!live.canSend || !live.draft.trim()">전송</button>
    </form>
  </aside>
</template>

<style scoped>
.ai-panel { display: flex; flex-direction: column; gap: 16px; min-height: 480px; }
.ai-tabs { display: grid; grid-template-columns: repeat(3, 1fr); padding: 3px 10px; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface-2); }
.ai-tabs button { padding: 9px 0; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--text-muted); font-size: 12px; }
.ai-tabs button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); font-weight: 700; }
.ai-body { flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 0; overflow-y: auto; }
.bubble { padding: 14px 15px; border-radius: 8px; font-size: 12px; line-height: 1.7; }
.bubble p { margin: 4px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.bubble small { font-size: 12px; font-weight: 700; }
.bubble.user { align-self: flex-end; width: 88%; background: var(--bubble); color: var(--bubble-text); }
.bubble.user small { opacity: .8; }
.bubble.ai { border: 1px solid var(--border); background: var(--surface-2); }
.sensor-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sensor-table th, .sensor-table td { padding: 8px 4px; border-bottom: 1px solid var(--border); text-align: left; }
.sensor-table td { text-align: right; }
.sensor-table tr.hot th, .sensor-table tr.hot td:nth-child(2) { color: var(--danger); }
.doc-link { display: block; text-decoration: none; }
.composer-row { display: flex; align-items: center; gap: 9px; padding: 9px 9px 9px 15px; border: 1px solid var(--border); border-radius: 9px; background: var(--surface-2); }
.composer-row textarea { flex: 1; min-width: 0; border: 0; outline: 0; resize: none; background: transparent; color: var(--text); font-size: 12px; }
.send { min-height: 36px; padding: 0 16px; font-size: 12px; }
</style>
