<script setup lang="ts">
// 1 이상 탐지 → 5 기록. `current` is the page being shown; earlier steps render as done.
defineProps<{ current: 1 | 2 | 3 | 4 | 5 }>()
const steps = ['이상 탐지', 'AI 조사', '원인 확인', '조치', '기록']
</script>

<template>
  <ol class="t-steps" aria-label="알람 처리 단계">
    <li v-for="(label, index) in steps" :key="label"
      :class="{done: index + 1 < current, current: index + 1 === current}"
      :aria-current="index + 1 === current ? 'step' : undefined">
      <i aria-hidden="true"></i>
      <span>{{ index + 1 }}&nbsp; {{ label }}</span>
    </li>
  </ol>
</template>
