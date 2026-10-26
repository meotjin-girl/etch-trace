<script setup lang="ts">
import StepBar from './StepBar.vue'

defineProps<{ title: string, subtitle?: string, ruled?: boolean, step?: 1 | 2 | 3 | 4 | 5 }>()
</script>

<template>
  <header class="t-page-head" :class="{ruled}">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle || $slots.subtitle"><slot name="subtitle">{{ subtitle }}</slot></p>
    </div>
    <StepBar v-if="step" :current="step" />
  </header>
</template>
