import { beforeEach, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ReportView from '@/components/ReportView.vue'
import RecordDetail from '@/components/RecordDetail.vue'
import { renderMarkdown } from '@/lib/markdown'
import { legacyRecords } from '@/stores/records'

const attack = '<img src=x onerror=alert(1)>"'

beforeEach(() => setActivePinia(createPinia()))

test('all report input is escaped including attributes and numeric fallbacks', () => {
  const wrapper = mount(ReportView, {props:{report:{context:{equipment:attack}, summary:attack,
    metrics:[{key:attack, value:attack, severity:attack}],
    causeCases:[{id:attack, cause:attack, action:attack, docs:[attack]}], docIds:[attack]}}})
  expect(wrapper.find('img').exists()).toBe(false)
  expect(wrapper.html()).toContain('&lt;img')
  expect(wrapper.text()).not.toContain('NaN')
  expect(wrapper.text()).toContain('미제공')
})

test('legacy records render read-only without resume or review actions', () => {
  const router = createRouter({history:createMemoryHistory(), routes:[{path:'/', component:{template:'<div/>'}}]})
  const [record] = (() => {
    const stored = JSON.stringify([{id:'OLD-1', context:{symptom:'fixture'}, documents:[]}])
    const original = globalThis.localStorage
    Object.defineProperty(globalThis, 'localStorage', {value:{getItem:() => stored}, configurable:true})
    try { return legacyRecords() } finally { Object.defineProperty(globalThis, 'localStorage', {value:original, configurable:true}) }
  })()
  const wrapper = mount(RecordDetail, {props:{task:record!}, global:{plugins:[router]}})
  expect(wrapper.text()).toContain('읽기 전용 로컬 기록')
  expect(wrapper.findAll('button.record-button')).toHaveLength(0)
})

test('markdown escapes raw HTML and only links safe protocols', () => {
  const html = renderMarkdown(`${attack}\n\n[ok](https://example.test) [bad](javascript:alert(1))`)
  expect(html).not.toContain('<img')
  expect(html).toContain('href="https://example.test"')
  expect(html).not.toContain('javascript:')
})

test('app shell mounts every route with backend data', async () => {
  const {default: App} = await import('@/App.vue')
  const {default: router} = await import('@/router')
  const {useIdentityStore} = await import('@/stores/identity')
  const task = {id:'t1', status:'WAITING_APPROVAL', question:'질문', user_name:'이엔지니어', user_role:'engineer',
    report:{documents:[{id:'DOC#1', title:'문서', text:'본문'}], docIds:['DOC#1'], metrics:[], causeCases:[]}, events:[]}
  useIdentityStore().api = {
    list: async () => [task], detail: async () => task, stream: () => () => {},
    sops: async () => [{id:'SOP-ETCH-12', title:'식각 공정 이상 대응 절차', category:'공정', version:'1.2',
      updatedAt:'2026-10-12', owner:'공정기술팀', description:'설명', tags:[], demo:true}],
    sop: async (id: string) => ({id, title:'식각 공정 이상 대응 절차', category:'공정', version:'1.2',
      updatedAt:'2026-10-12', owner:'공정기술팀', description:'설명', tags:[], demo:true, markdown:'## 목적'}),
  } as never
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) { this.open = true }
  globalThis.matchMedia ??= (() => ({matches:false})) as never
  const wrapper = mount(App, {global:{plugins:[router]}, attachTo:document.body})
  // [path, expected text, progress card visible]
  const pages: [string, string, boolean][] = [
    ['/', '어떤 이상을 조사할까요?', true], ['/records', '조사 기록을 선택해 주세요', false],
    ['/records/t1', '조사 열기 / 이어가기', true], ['/sop', 'SOP-ETCH-12', false]]
  for (const [path, expected, progress] of pages) {
    await router.push(path)
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(wrapper.text()).toContain(expected)
    expect(wrapper.find('.process-card').exists()).toBe(progress)
  }
  await router.push('/records/t1')
  await new Promise(resolve => setTimeout(resolve, 0))
  expect(wrapper.find('[data-evidence-id="DOC#1"]').exists()).toBe(true)
  wrapper.unmount()
})

test('pending judgement renders 승인/미승인 under the report bubble', async () => {
  const {default: InvestigationView} = await import('@/views/InvestigationView.vue')
  const {useInvestigationStore} = await import('@/stores/investigation')
  const investigation = useInvestigationStore()
  investigation.task = {id:'a', status:'WAITING_APPROVAL', question:'질문', user_name:'이엔지니어'}
  investigation.events = [{seq:1, type:'QUEUED', payload:{}},
    {seq:2, type:'APPROVAL_REQUIRED', payload:{report:{summary:'요약'}, text:'보고서를 판별해 주세요'}}]
  const wrapper = mount(InvestigationView)
  const buttons = wrapper.findAll('.quick-replies button').map(button => button.text())
  expect(buttons).toEqual(['승인', '미승인'])
  expect(wrapper.text()).toContain('보고서를 판별해 주세요')
  expect(wrapper.find('textarea').attributes('disabled')).toBeUndefined()
})

test('report renders develop sections: stages, approved history, RAG checks with citations', () => {
  const wrapper = mount(ReportView, {props:{report:{summary:'요약', demo:true,
    stages:[{key:'scope', title:'범위 조사 에이전트', status:'sample_based', agent_mode:'llm', findings:['사례 3건'], unknowns:['MES 미연결']}],
    history:[{id:'HIST-1', question:'과거 질문', summary:'과거 요약', causes:['RF'], approvedBy:'이엔지니어', approvedAt:'2026-10-12', lotId:'LOT-1'}],
    checks:[{title:'SOP-ETCH-12 · 4.2', rationale:'동시 비교', source:'rag_mcp', docId:'SOP-ETCH-12#4.2'}]}}})
  const text = wrapper.text()
  for (const expected of ['조사 단계별 결과', '데모 사례 기반 · LLM 사용', '미확인: MES 미연결',
    '유사 승인 조사 이력', '과거 후보: RF', 'Lot LOT-1', 'SOP RAG 검색 결과 · 우선 확인 순서', '[SOP-ETCH-12#4.2]']) {
    expect(text).toContain(expected)
  }
  expect(wrapper.findAll('button.citation').map(button => button.text())).toContain('[SOP-ETCH-12#4.2]')
})
