import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { createApi } from '@/api/client'
import { createLiveApi } from '@/api/live-investigations'
import { createAgentApi } from '@/api/agent-server'
import { createAuth, type AuthStatus } from '@/auth'
import type { Role } from '@/api/types'
import { useInvestigationStore } from './investigation'
import { useRecordsStore } from './records'
import { useLiveInvestigationsStore } from './live-investigations'

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
      useLiveInvestigationsStore().reset()
    }
  }})
  const mock = __TRACE_MOCK__ && import.meta.env.DEV
  const session = mock ? {
    getToken: async () => 'trace-mock-user', invalidate: () => {},
  } : auth
  const api = shallowRef(createApi(session))
  const liveApi = shallowRef(createLiveApi(session))
  const agentApi = shallowRef(createAgentApi(session))
  async function init() {
    if (!mock) return auth.init()
    name.value = '목업 사용자'
    subject.value = 'mock-user'
    status.value = 'authenticated'
  }
  return {name, subject, role, status, error, api, liveApi, agentApi, init, login: auth.login, logout: auth.logout}
})
