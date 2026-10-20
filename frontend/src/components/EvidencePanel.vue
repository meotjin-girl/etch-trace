<script setup>
import { computed } from 'vue'
const props = defineProps({ events: Array })
const last = (name) => [...props.events].reverse().find((e) => e.type === 'TOOL_END' && e.name === name && e.ok)?.result
const ctx = computed(() => last('get_run_context'))
const refs = computed(() => last('find_reference_runs'))
const cmp = computed(() => last('compare_signals'))
const docs = computed(() => props.events.filter((e) => e.type === 'TOOL_END' && e.name === 'search_knowledge' && e.ok).flatMap((e) => e.result.docs || []))
const uniqDocs = computed(() => [...new Map(docs.value.map((d) => [d.source + d.section, d])).values()])
const zNum = (z) => (typeof z === 'number' ? z : 99)
const tone = (z) => (Math.abs(zNum(z)) >= 3 ? 'tone-bad' : Math.abs(zNum(z)) >= 2 ? 'tone-warn' : 'tone-neutral')
</script>
<template>
  <div class="grid">
    <div v-if="ctx">
      <h3>대상 run</h3>
      <p class="mono">{{ ctx.tool }} · run {{ ctx.run_id }} · recipe {{ ctx.recipe }} · stage {{ ctx.stage }} · {{ Math.round(ctx.duration_sec / 60) }}분 · steps {{ ctx.steps.length }}</p>
      <p v-if="ctx.recent_faults?.length" class="muted">이전 고장: {{ ctx.recent_faults.map((f) => `${f.fault_name} (${f.hours_before_run_end}h 전)`).join(', ') }}</p>
    </div>
    <div v-if="refs">
      <h3>비교 기준</h3>
      <p class="muted">{{ refs.criteria }}</p>
      <div class="chips"><span v-for="r in refs.reference_run_ids" :key="r" class="chip">{{ r }}</span></div>
    </div>
    <div v-if="cmp">
      <h3>신호 편차 상위 (코드 계산 · |z| ≥ 3: {{ cmp.flagged_abs_z_ge_3 }}건 / {{ cmp.compared_pairs }}쌍)</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>step</th><th>센서</th><th>z</th><th class="num">대상</th><th class="num">참조 평균±표준편차</th></tr></thead>
          <tbody>
            <tr v-for="d in cmp.top" :key="d.step + d.signal">
              <td class="mono">{{ d.step }}</td><td class="mono">{{ d.signal }}</td>
              <td><span class="badge" :class="tone(d.z)">{{ d.z }}</span></td>
              <td class="num">{{ d.target_mean }}</td><td class="num">{{ d.ref_mean }} ± {{ d.ref_std }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="muted" style="margin-top:6px;font-size:12px">{{ cmp.method }}</p>
    </div>
    <div v-if="uniqDocs.length">
      <h3>문서 근거 (pgvector)</h3>
      <details v-for="d in uniqDocs" :key="d.source + d.section">
        <summary><span class="mono">{{ d.source }}</span> › {{ d.section }} <span class="muted">· 유사도 {{ d.score }}</span></summary>
        <p class="doc">{{ d.content }}</p>
      </details>
    </div>
    <p v-if="!ctx && !cmp && !uniqDocs.length" class="muted">도구 결과가 들어오면 여기에 근거가 쌓입니다.</p>
  </div>
</template>
<style scoped>
details { border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; margin-bottom: 6px; }
summary { cursor: pointer; font-size: 13px; } .doc { white-space: pre-wrap; font-size: 13px; margin-top: 8px; color: var(--muted); }
</style>
