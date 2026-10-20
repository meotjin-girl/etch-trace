<script setup>
defineProps({ report: Object })
const SECTIONS = [
  ['facts', '01 · FACTS', '비교 조건과 계산 결과'],
  ['evidence', '02 · EVIDENCE', '데이터·문서 출처'],
  ['next_actions', '03 · NEXT ACTION', '사람이 추가 확인할 항목'],
  ['unknowns', '04 · UNKNOWN', '확인하지 못한 것·데이터 한계'],
]
</script>
<template>
  <div v-if="report" class="report">
    <p class="summary">{{ report.summary }}</p>
    <section v-for="[k, title, sub] in SECTIONS" :key="k">
      <h3>{{ title }} <span class="muted">{{ sub }}</span></h3>
      <ul><li v-for="(x, i) in report[k]" :key="i">{{ x }}</li></ul>
    </section>
  </div>
</template>
<style scoped>
.summary { font-weight: 600; padding: 10px 12px; border-left: 3px solid var(--accent); background: var(--accent-soft); border-radius: 0 8px 8px 0; }
section { margin-top: 14px; } h3 span { text-transform: none; letter-spacing: 0; font-weight: 500; }
ul { margin: 0; padding-left: 18px; } li { margin-bottom: 4px; }
</style>
