import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { createApi } from '@/api/client'
import { createAuth, type AuthStatus } from '@/auth'
import type { Role } from '@/api/types'
import { useInvestigationStore } from './investigation'
import { useRecordsStore } from './records'

export const useIdentityStore = defineStore('identity', () => {
  const name = ref('')
  const subject = ref('')
  const role = ref<Role>('user')
  const status = ref<AuthStatus>('loading')
  const error = ref('')
  const auth = createAuth({onChange(session) {
    const wasAuthenticated = status.value === 'authenticated'
    status.value = session.status
    name.value = session.name
    subject.value = session.subject
    error.value = session.error
    if (wasAuthenticated && session.status !== 'authenticated') {
      useRecordsStore().abort()
      useInvestigationStore().reset()
      useRecordsStore().clear()
    }
  }})
  const mock = __TRACE_MOCK__ && import.meta.env.DEV
  const api = shallowRef(createApi(mock ? {
    getToken: async () => 'trace-mock-user', invalidate: () => {},
  } : auth))
  async function init() {
    if (!mock) return auth.init()
    name.value = '목업 사용자'
    subject.value = 'mock-user'
    status.value = 'authenticated'
  }
  return {name, subject, role, status, error, api, init, login: auth.login, logout: auth.logout}
})
