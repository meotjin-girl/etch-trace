<script setup>
import { useRouter } from 'vue-router'
import { session, ROLES, logout } from './api'

const router = useRouter()
function out() {
  logout()
  router.push('/')
}
</script>

<template>
  <header class="topbar">
    <div class="brand"><span class="mark">⌁</span> TRACE <small>식각 공정 이상 조사 Agent</small></div>
    <div v-if="session.role" class="who">
      <span class="role-chip" :data-role="session.role">{{ ROLES[session.role].label }}</span>
      <span>{{ session.name }}</span>
      <button class="ghost" @click="out">로그아웃</button>
    </div>
  </header>
  <main><router-view /></main>
</template>
