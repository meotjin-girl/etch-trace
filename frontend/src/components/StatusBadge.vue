<script setup>
import { STATUS } from '../api'
defineProps({ status: String })
</script>
<template>
  <span class="badge" :class="`tone-${STATUS[status]?.tone || 'neutral'}`">{{ STATUS[status]?.label || status }}</span>
</template>
