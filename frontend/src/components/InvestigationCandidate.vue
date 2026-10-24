<script setup lang="ts">
import type { Candidate } from '@/api/live-models'

defineProps<{ candidate: Candidate }>()
</script>

<template>
  <article class="evidence-item" :data-candidate-id="candidate.id">
    <header><strong>{{ candidate.cause }}</strong></header>
    <p class="report-text"><b>권고 조치</b><br>{{ candidate.action }}</p>
    <p class="report-text"><b>판단 근거</b><br>{{ candidate.rationale }}</p>
    <template v-for="group in [
      {label:'확인 항목', values:candidate.checks},
      {label:'근거 사례', values:candidate.case_ids},
      {label:'근거 문서', values:candidate.doc_ids},
      {label:'미확인 사항', values:candidate.unknowns},
    ]" :key="group.label">
      <p><b>{{ group.label }}</b></p>
      <ul class="detail-evidence">
        <li v-for="(item, index) in group.values" :key="index">{{ item }}</li>
        <li v-if="!group.values.length">미제공</li>
      </ul>
    </template>
    <slot />
  </article>
</template>
