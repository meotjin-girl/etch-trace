<script setup lang="ts">
// One Flaticon family keeps stroke weight and rounded corners consistent.
const icons = {
  alarms: 'bell', records: 'search-alt', book: 'book-alt', settings: 'settings',
  search: 'search', logout: 'sign-out-alt', ai: 'sparkles', chat: 'comment-alt',
  sensors: 'chart-line-up', document: 'document', events: 'list', selected: 'bullseye',
  info: 'file-circle-info', warning: 'triangle-warning', forward: 'arrow-small-right',
  back: 'arrow-small-left', up: 'arrow-small-up', chevron: 'angle-small-right',
  check: 'check', refresh: 'refresh', close: 'cross-small', send: 'paper-plane',
} as const

defineProps<{ name: keyof typeof icons }>()
</script>

<template>
  <i class="trace-icon fi" :class="`fi-rr-${icons[name]}`" aria-hidden="true"></i>
</template>

<style scoped>
.trace-icon { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; width: 1em; height: 1em; font-size: 1em; line-height: 1; vertical-align: -.125em; }
.trace-icon::before { display: block; }
</style>
