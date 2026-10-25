<script setup lang="ts">
defineProps<{ title: string, subtitle?: string, ruled?: boolean }>()
</script>

<template>
  <header class="t-page-head" :class="{ruled}">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle || $slots.subtitle"><slot name="subtitle">{{ subtitle }}</slot></p>
    </div>
    <span class="t-tag">합성 데이터</span>
  </header>
</template>
