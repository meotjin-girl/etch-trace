<script setup lang="ts">
defineProps<{ role: 'user' | 'assistant' }>()
</script>

<template>
  <div class="message" :class="role === 'user' ? 'user-message' : 'assistant-message'">
    <div class="avatar">{{ role === 'user' ? '나' : 'AI' }}</div>
    <div class="message-body"><slot /></div>
  </div>
</template>
