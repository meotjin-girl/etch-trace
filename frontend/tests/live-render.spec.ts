import { expect, test } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import LiveInvestigationsView from '@/views/LiveInvestigationsView.vue'
import LiveInvestigationView from '@/views/LiveInvestigationView.vue'
import { useIdentityStore } from '@/stores/identity'
import { createLiveApi } from '@/api/live-investigations'
import { createAgentApi } from '@/api/agent-server'
import type { LiveInvestigation } from '@/api/live-models'
import { candidate, detail, json, snapshot, sse, summary, values } from './live-fixtures'

test('list to detail to approval to continued conversation renders distinct immutable and live candidates', async () => {
  // Given real frontend clients over a deterministic HTTP boundary.
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  let record: LiveInvestigation = {...detail}
  let history: unknown[] = [
    {type:'human', id:'u', content:'Initial alert'},
    {type:'ai', id:'tool-call', content:'Hidden intermediate', tool_calls:[{name:'search'}]},
    {type:'tool', content:'Hidden result'},
    {type:'ai', id:'a', content:'Initial analysis'},
  ]
  const mutations: {url: string, body: unknown}[] = []
  const fetcher: typeof fetch = async (input, init = {}) => {
    const url = String(input)
    if (init.method === 'POST') mutations.push({url, body:JSON.parse(String(init.body))})
    if (url === '/api/investigations') return json([summary])
    if (url.endsWith('/approval')) { record = {...record, approval:snapshot}; return json(snapshot) }
    if (url.startsWith('/api/investigations/')) return json(record)
    if (url.endsWith('/state')) return json({values:{messages:history}})
    if (url.includes('/runs?')) return json([])
    if (url.endsWith('/runs/stream')) {
      record = {...record, revision:4, candidates:[{...candidate, cause:'New live cause <img src=x onerror=alert(1)>'}]}
      history = [...history, {type:'human', id:'u2', content:'More evidence'}, {type:'ai', id:'a2', content:'Post-approval reply'}]
      return sse(values(history))
    }
    throw new Error(`Unexpected request ${url}`)
  }
  const auth = {getToken:async () => 'token', invalidate() {}}
  identity.liveApi = createLiveApi(auth, {fetch:fetcher})
  identity.agentApi = createAgentApi(auth, {fetch:fetcher})
  const router = createRouter({history:createMemoryHistory(), routes:[
    {path:'/', component:LiveInvestigationsView},
    {path:'/investigations/:id', component:LiveInvestigationView},
  ]})
  await router.push('/')
  const wrapper = mount({template:'<RouterView />'}, {global:{plugins:[router]}})
  await flushPromises()
  // When opening a listed investigation, approving its candidate and asking a follow-up.
  await wrapper.get(`[data-investigation-id="${detail.id}"]`).trigger('click')
  await flushPromises()
  expect(wrapper.get('[data-testid="thread-conversation"]').text()).not.toContain('Hidden')
  await wrapper.get(`[data-approve-candidate="${candidate.id}"]`).trigger('click')
  await flushPromises()
  expect(wrapper.get('#threadQuestion').attributes('disabled')).toBeUndefined()
  await wrapper.get('#threadQuestion').setValue('More evidence')
  await wrapper.get('[data-testid="thread-composer"]').trigger('submit')
  await flushPromises()
  // Then the current candidates change, the old snapshot remains, and chat stays usable.
  expect(wrapper.get('[data-testid="current-candidates"]').text()).toContain('New live cause')
  expect(wrapper.get('[data-testid="approved-snapshot"]').text()).toContain(candidate.cause)
  expect(wrapper.get('[data-testid="approved-snapshot"]').text()).not.toContain('New live cause')
  expect(wrapper.find('img').exists()).toBe(false)
  expect(wrapper.get('[data-testid="thread-conversation"]').text()).toContain('Post-approval reply')
  expect(wrapper.get('#threadQuestion').attributes('disabled')).toBeUndefined()
  expect(wrapper.find('[data-approve-candidate]').exists()).toBe(false)
  expect(mutations).toEqual([
    {url:`/api/investigations/${detail.id}/approval`, body:{candidate_id:candidate.id, expected_revision:3, comment:''}},
    {url:`/agent/threads/${detail.thread_id}/runs/stream`, body:{
      assistant_id:'trace', input:{request:{role:'user', content:'More evidence'}},
      stream_mode:['values'], multitask_strategy:'reject', on_disconnect:'continue',
    }},
  ])
  wrapper.unmount()
})
