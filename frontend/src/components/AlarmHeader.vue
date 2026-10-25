<script setup lang="ts">
import type { LiveInvestigation } from '@/api/live-models'
import { fixed, stageLabels, stageOf, type headline } from '@/lib/alert-text'

defineProps<{ investigation: LiveInvestigation, head: ReturnType<typeof headline> }>()
</script>

<template>
  <section class="t-card alarm-header" aria-label="알람 요약">
    <div class="row">
      <strong>{{ investigation.alert.tool_id }} / {{ investigation.alert.chamber_id }}</strong>
      <span class="t-pill" :class="stageOf(investigation)">{{ stageLabels[stageOf(investigation)] }}</span>
    </div>
    <div class="row">
      <strong v-if="head" class="t-mono">
        {{ head.alarm.rule }} · 측정 {{ fixed(head.value) }} {{ head.unit }}<template v-if="head.mean !== null"> / 정상 {{ fixed(head.mean, 2) }}</template>
      </strong>
      <strong v-else>{{ investigation.summary }}</strong>
      <span class="t-faint">{{ investigation.alert.lot_id }} · {{ head?.alarm.time ?? '' }} KST · 합성 이벤트</span>
    </div>
  </section>
</template>

<style scoped>
.alarm-header { display: grid; gap: 18px; margin-bottom: 28px; }
.row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.row strong { font-size: 21px; font-weight: 800; }
</style>
