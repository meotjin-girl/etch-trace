<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useIdentityStore } from '@/stores/identity'
import { useUiStore } from '@/stores/ui'

const identity = useIdentityStore()
const ui = useUiStore()
const route = useRoute()
const section = computed(() => String(route.meta.section ?? ''))
const nav = [
  {to:'/', section:'alarms', icon:'fi-rr-apps', label:'이상 로그'},
  {to:'/records', section:'records', icon:'fi-rr-document', label:'조사 기록'},
  {to:'/sop', section:'sop', icon:'fi-rr-book-alt', label:'SOP · OCAP'},
]
// Two-letter badge from the account name (Latin initials, or the first two Hangul syllables).
const initials = computed(() => {
  const name = identity.name.trim()
  const words = name.split(/\s+/).filter(Boolean)
  if (/^[A-Za-z]/.test(name)) return words.slice(0, 2).map(word => word[0]!.toUpperCase()).join('')
  return name.slice(0, 2)
})
const roleLabel = computed(() => identity.role === 'engineer' ? '엔지니어' : identity.role === 'admin' ? '관리자' : '근무자')
</script>

<template>
  <aside class="t-sidebar" aria-label="서비스 탐색">
    <RouterLink to="/" class="t-brand" aria-label="TRACE 홈">
      <svg width="26" height="26" viewBox="0 0 34 34" aria-hidden="true">
        <rect x="7" y="7" width="20" height="20" transform="rotate(45 17 17)" fill="none" stroke="currentColor" stroke-width="2.4" />
      </svg>
      <strong>TRACE</strong>
    </RouterLink>
    <p class="t-brand-sub">식각 공정 이상 조사</p>

    <label class="t-search">
      <i class="fi-rr-search" aria-hidden="true"></i>
      <span class="sr-only">알람·장비 검색</span>
      <input v-model="ui.search" type="search" placeholder="알람·장비 검색" autocomplete="off">
    </label>

    <p class="t-nav-label">WORKSPACE</p>
    <nav aria-label="조사 메뉴">
      <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="t-nav-item"
        :class="{active: section === item.section}" :aria-current="section === item.section ? 'page' : undefined">
        <i :class="item.icon" aria-hidden="true"></i>{{ item.label }}
      </RouterLink>
    </nav>
    <hr class="t-divider">
    <button type="button" class="t-nav-item t-settings" disabled title="준비 중">설정</button>

    <div class="t-user">
      <b aria-hidden="true">{{ initials }}</b>
      <span>{{ identity.name }} · {{ roleLabel }}</span>
      <button type="button" title="로그아웃" aria-label="로그아웃" @click="identity.logout()"><i class="fi-rr-sign-out-alt" aria-hidden="true"></i></button>
    </div>
  </aside>
</template>
