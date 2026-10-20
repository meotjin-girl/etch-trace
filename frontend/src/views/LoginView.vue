<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ROLES, login } from '../api'

const router = useRouter()
const name = ref('')
const DEFAULT_NAME = { worker: '김작업', engineer: '이엔지', admin: '박관리' }
function enter(role) {
  login(name.value.trim() || DEFAULT_NAME[role], role)
  router.push(ROLES[role].home)
}
</script>
<template>
  <section class="login">
    <h1>역할을 선택해 들어가세요</h1>
    <p class="muted">시연용 목업 로그인입니다. 다음 단계에서 Supabase Auth로 교체합니다. 화면 분기는 화면에서, 권한 검사는 서버에서 합니다.</p>
    <label for="nm">이름 (비우면 기본 이름)</label>
    <input id="nm" v-model="name" placeholder="예: 김작업" maxlength="20" />
    <div class="roles">
      <button v-for="(r, key) in ROLES" :key="key" class="role" @click="enter(key)">
        <span class="role-chip" :data-role="key">{{ r.label }}</span>
        <span class="desc">{{ r.desc }}</span>
      </button>
    </div>
  </section>
</template>
<style scoped>
.login { max-width: 640px; margin: 40px auto; }
.roles { display: grid; gap: 10px; margin-top: 16px; }
.role { display: flex; align-items: center; gap: 12px; text-align: left; background: var(--panel); color: var(--ink); border: 1px solid var(--line); padding: 14px 16px; }
.role:hover { border-color: var(--accent); } .desc { color: var(--muted); font-weight: 500; }
</style>
