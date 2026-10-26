import { expect, test } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import AiPanel from '@/components/AiPanel.vue'
import { parseAlert } from '@/lib/alert-text'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'
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

test('alarm log → proposal → candidate → choose → re-choose → review → action record → records', async () => {
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
    if (init.method === 'DELETE') { mutations.push({url, body:null}); record = {...record, approval:null}; return new Response(null, {status:204}) }
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

  // Before any action is recorded the choice can be cleared and made again.
  await wrapper.get('[data-testid="rechoose"]').trigger('click')
  await flushPromises()
  expect(router.currentRoute.value.path).toBe(`/investigations/${detail.id}`)
  await router.push(`/investigations/${detail.id}/candidates/${candidate.id}`)
  await flushPromises()
  await wrapper.get(`[data-approve-candidate="${candidate.id}"]`).trigger('click')
  await flushPromises()
  expect(router.currentRoute.value.path).toBe(`/investigations/${detail.id}/action`)

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
    {url:`/api/investigations/${detail.id}/approval`, body:null},
    {url:`/api/investigations/${detail.id}/approval`, body:{candidate_id:candidate.id, expected_revision:3, comment:''}},
    {url:`/api/investigations/${detail.id}/action`, body:{content:action.content, result:action.result}},
  ])
  wrapper.unmount()
})


test('question is visible before stream resolution, old state keeps it, echo replaces it', async () => {
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  let channel!: ReadableStreamDefaultController<Uint8Array>
  const fetcher: typeof fetch = async input => {
    const url = String(input)
    if (url.startsWith('/api/')) return json(detail)
    if (url.endsWith('/state')) return json({values:{messages:[]}})
    if (url.includes('/runs?')) return json([])
    return new Response(new ReadableStream({start(controller) { channel = controller }}),
      {headers:{'Content-Type':'text/event-stream'}})
  }
  const auth = {getToken:async () => 'token', invalidate() {}}
  identity.liveApi = createLiveApi(auth, {fetch:fetcher})
  identity.agentApi = createAgentApi(auth, {fetch:fetcher})
  const live = useLiveInvestigationsStore()
  await live.open(detail.id)
  const wrapper = mount(AiPanel, {props:{investigation:detail, parsed:parseAlert(detail.alert.source_text)},
    global:{stubs:{RouterLink:true}}})
  await wrapper.get('#threadQuestion').setValue('Why?')
  await wrapper.get('[data-testid="thread-composer"]').trigger('submit')
  expect(wrapper.get('.bubble.user').text()).toBe('Why?')
  expect(wrapper.findAll('.typing span')).toHaveLength(3)
  await flushPromises()
  channel.enqueue(new TextEncoder().encode(values([])))
  await flushPromises()
  expect(wrapper.get('.bubble.user').text()).toBe('Why?')
  channel.enqueue(new TextEncoder().encode(values([{type:'human', id:'new', content:'Why?'},
    {type:'ai', id:'answer', content:'Because RF drifted'}])))
  await flushPromises()
  expect(wrapper.findAll('.bubble.user')).toHaveLength(1)
  expect(live.pending).toBe('')
  expect(wrapper.get('[data-testid="thread-message"]').text()).toBe('Because RF drifted')
  channel.close()
  await flushPromises()
  expect(wrapper.find('.typing').exists()).toBe(false)
  wrapper.unmount()
  live.close()
})

test('empty-state suggestion sends its question and shows errors above the composer', async () => {
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  const sent: string[] = []
  const fetcher: typeof fetch = async (input, init = {}) => {
    const url = String(input)
    if (url.startsWith('/api/')) return json(detail)
    if (url.endsWith('/state')) return json({values:{messages:[]}})
    if (url.includes('/runs?')) return json([])
    sent.push(JSON.parse(String(init.body)).input.request.content)
    return json({detail:'Agent unavailable'}, 503)
  }
  const auth = {getToken:async () => 'token', invalidate() {}}
  identity.liveApi = createLiveApi(auth, {fetch:fetcher})
  identity.agentApi = createAgentApi(auth, {fetch:fetcher})
  const live = useLiveInvestigationsStore()
  await live.open(detail.id)
  const wrapper = mount(AiPanel, {props:{investigation:detail, parsed:parseAlert(detail.alert.source_text)},
    global:{stubs:{RouterLink:true}}})
  await wrapper.get('.suggestions button').trigger('click')
  await flushPromises()
  expect(sent).toEqual(['가장 유력한 원인은?'])
  expect(wrapper.get('.chat-error').text()).toBeTruthy()
  expect(live.pending).toBe('')
  expect(wrapper.get<HTMLTextAreaElement>('#threadQuestion').element.value).toBe('가장 유력한 원인은?')
  wrapper.unmount()
  live.close()
})
