<script setup lang="ts">
import type { LiveInvestigation } from '@/api/live-models'
import { fixed, stageLabels, stageOf, type headline } from '@/lib/alert-text'

defineProps<{ investigation: LiveInvestigation, head: ReturnType<typeof headline> }>()
</script>

<template>
  <section class="alarm-header" aria-label="알람 요약">
    <span class="t-pill" :class="stageOf(investigation)">{{ stageLabels[stageOf(investigation)] }}</span>
    <strong v-if="head" class="t-mono">
      {{ head.alarm.rule }} · 측정 {{ fixed(head.value) }} {{ head.unit }}<template v-if="head.mean !== null"> / 정상 {{ fixed(head.mean, 2) }}</template>
    </strong>
    <strong v-else>{{ investigation.summary }}</strong>
    <span class="t-faint">{{ investigation.alert.lot_id }} · {{ head?.alarm.time ?? '' }} KST</span>
  </section>
</template>

<style scoped>
.alarm-header { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin-bottom: 14px; padding: 9px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
.alarm-header strong { font-size: 14px; font-weight: 800; }
.alarm-header .t-faint { margin-left: auto; font-size: 12px; }
</style>
