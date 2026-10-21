<script setup lang="ts">
import { useIdentityStore } from '@/stores/identity'

const identity = useIdentityStore()
</script>

<template>
  <main class="auth-gate">
    <section class="auth-panel" aria-labelledby="login-title">
      <p class="eyebrow">FAB INSIGHT</p>
      <h1 id="login-title">식각 장비 이상 조사</h1>
      <p>팀 계정으로 로그인해 조사를 이어가세요.</p>
      <p v-if="identity.error" role="alert">{{ identity.error }}</p>
      <p v-if="identity.status === 'loading' || identity.status === 'redirecting'" role="status">
        {{ identity.status === 'loading' ? '로그인 상태를 확인하고 있습니다.' : '로그인 화면으로 이동합니다.' }}
      </p>
      <button v-else-if="identity.status === 'error'" type="button" class="primary-button" @click="identity.init()">
        다시 연결
      </button>
      <button v-else type="button" class="primary-button" @click="identity.login()">로그인</button>
    </section>
  </main>
</template>

<style scoped>
.auth-gate { min-height: 100dvh; display: grid; place-items: center; padding: 24px; }
.auth-panel { width: min(100%, 440px); padding: 24px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.auth-panel h1 { margin: 0 0 24px; font-size: 25px; }
.auth-panel p:not(.eyebrow) { font-size: 15px; line-height: 1.65; margin: 0 0 24px; overflow-wrap: anywhere; }
.auth-panel .eyebrow { color: var(--muted); }
</style>
