import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { createApi } from '@/api/client'
import type { Identity, Role } from '@/api/types'
import { useInvestigationStore } from './investigation'
import { useRecordsStore } from './records'

export const useIdentityStore = defineStore('identity', () => {
  const name = ref('이엔지니어')
  const role = ref<Role>('engineer')
  const identity = (): Identity => ({name: name.value, role: role.value})
  // Replaced on identity change; tests inject a fake through `api`.
  const api = shallowRef(createApi(identity()))

  function change(nextName: string, nextRole: Role) {
    const investigation = useInvestigationStore()
    const records = useRecordsStore()
    records.abort()
    investigation.reset()
    name.value = nextName.trim() || name.value
    role.value = nextRole
    api.value = createApi(identity())
    records.clear()
    records.refresh()
  }

  return {name, role, api, change}
})
