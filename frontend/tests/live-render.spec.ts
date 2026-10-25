import { expect, test } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import AlarmLogView from '@/views/AlarmLogView.vue'
import ProposalView from '@/views/ProposalView.vue'
import CandidateView from '@/views/CandidateView.vue'
import ActionReviewView from '@/views/ActionReviewView.vue'
import ActionRecordView from '@/views/ActionRecordView.vue'
import InvestigationRecordsView from '@/views/InvestigationRecordsView.vue'
import { useIdentityStore } from '@/stores/identity'
import { createLiveApi } from '@/api/live-investigations'
import { createAgentApi } from '@/api/agent-server'
import type { InvestigationSummary, LiveInvestigation } from '@/api/live-models'
import { candidate, detail, json, snapshot, sse, summary, values } from './live-fixtures'

test('alarm log → proposal → candidate → choose → review → action record → records', async () => {
  // Given real frontend clients over a deterministic HTTP boundary.
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  let record: LiveInvestigation = {...detail}
  const listed = (): InvestigationSummary => ({...summary,
    approved_at:record.approval?.approved_at ?? null, action_recorded_at:record.action?.recorded_at ?? null})
  let history: unknown[] = [
    {type:'human', id:'u', content:record.alert.source_text},
    {type:'ai', id:'tool-call', content:'Hidden intermediate', tool_calls:[{name:'search'}]},
    {type:'tool', content:'Hidden result'},
    {type:'ai', id:'a', content:'Initial analysis'},
  ]
  const mutations: {url: string, body: unknown}[] = []
  const action = {content:'Checked RF match', result:'Reflected power back to 5 W',
    recorded_by_id:'engineer-1', recorded_by:'Engineer', recorded_at:'2026-10-23T10:05:00Z'}
  const fetcher: typeof fetch = async (input, init = {}) => {
    const url = String(input)
    if (init.method === 'POST') mutations.push({url, body:JSON.parse(String(init.body))})
    if (url === '/api/investigations') return json([listed()])
    if (url.endsWith('/approval')) { record = {...record, approval:snapshot}; return json(snapshot) }
    if (url.endsWith('/action')) { record = {...record, action}; return json(action) }
    if (url.startsWith('/api/investigations/')) return json(record)
    if (url.endsWith('/state')) return json({values:{messages:history}})
    if (url.includes('/runs?')) return json([])
    if (url.endsWith('/runs/stream')) {
      history = [...history, {type:'human', id:'u2', content:'Why did it rise?'}, {type:'ai', id:'a2', content:'Match drift <img src=x onerror=alert(1)>'}]
      return sse(values(history))
    }
    throw new Error(`Unexpected request ${url}`)
  }
  const auth = {getToken:async () => 'token', invalidate() {}}
  identity.liveApi = createLiveApi(auth, {fetch:fetcher})
  identity.agentApi = createAgentApi(auth, {fetch:fetcher})
  const router = createRouter({history:createMemoryHistory(), routes:[
    {path:'/', component:AlarmLogView},
    {path:'/investigations/:id', component:ProposalView},
    {path:'/investigations/:id/candidates/:cid', component:CandidateView},
    {path:'/investigations/:id/action', component:ActionReviewView},
    {path:'/investigations/:id/record', component:ActionRecordView},
    {path:'/records/:id?', component:InvestigationRecordsView},
    {path:'/sop/:id?', component:{template:'<p>sop</p>'}},
  ]})
  await router.push('/')
  const wrapper = mount({template:'<RouterView />'}, {global:{plugins:[router]}})
  await flushPromises()

  // The alarm card headlines the parsed equipment alarm, not the raw text.
  expect(wrapper.get(`[data-investigation-id="${detail.id}"]`).text()).toContain('RF 반사 전력 상승 · RF_REFLECT_HIGH')
  await wrapper.get('[data-testid="open-investigation"]').trigger('click')
  await flushPromises()
  const chat = wrapper.get('[data-testid="thread-conversation"]').text()
  expect(chat).toContain('Initial analysis')
  expect(chat).not.toContain('Hidden')
  expect(chat).not.toContain('[경보]')

  // A follow-up question streams into the panel, escaped.
  await wrapper.get('#threadQuestion').setValue('Why did it rise?')
  await wrapper.get('[data-testid="thread-composer"]').trigger('submit')
  await flushPromises()
  expect(wrapper.get('[data-testid="thread-conversation"]').text()).toContain('Match drift')
  expect(wrapper.find('img').exists()).toBe(false)

  await router.push(`/investigations/${detail.id}/candidates/${candidate.id}`)
  await flushPromises()
  await wrapper.get(`[data-approve-candidate="${candidate.id}"]`).trigger('click')
  await flushPromises()
  expect(router.currentRoute.value.path).toBe(`/investigations/${detail.id}/action`)
  expect(wrapper.get('[data-testid="approved-snapshot"]').text()).toContain(candidate.cause)

  await router.push(`/investigations/${detail.id}/record`)
  await flushPromises()
  const form = wrapper.get('[data-testid="action-form"]')
  const [content, result] = form.findAll('textarea')
  await content!.setValue(action.content)
  await result!.setValue(action.result)
  await form.trigger('submit')
  await flushPromises()
  expect(router.currentRoute.value.path).toBe(`/records/${detail.id}`)
  expect(wrapper.text()).toContain(action.result)

  expect(mutations).toEqual([
    {url:`/agent/threads/${detail.thread_id}/runs/stream`, body:{
      assistant_id:'trace', input:{request:{role:'user', content:'Why did it rise?'}},
      stream_mode:['values'], multitask_strategy:'reject', on_disconnect:'continue',
    }},
    {url:`/api/investigations/${detail.id}/approval`, body:{candidate_id:candidate.id, expected_revision:3, comment:''}},
    {url:`/api/investigations/${detail.id}/action`, body:{content:action.content, result:action.result}},
  ])
  wrapper.unmount()
})
