import { beforeEach, expect, test } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
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
  useIdentityStore().status = 'authenticated'
  useIdentityStore().liveApi.list = async () => []
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
  // [path, expected text, legacy evidence rail visible]
  const pages: [string, string, boolean][] = [
    ['/', '이상 탐지 상태의 알람이 없습니다', false], ['/records', '조사 기록이 아직 없습니다', false],
    ['/sop', 'SOP-ETCH-12', false], ['/legacy', '어떤 이상을 조사할까요?', true],
    ['/legacy/records/t1', '조사 열기 / 이어가기', true]]
  for (const [path, expected, legacy] of pages) {
    await router.push(path)
    await flushPromises()
    expect(wrapper.text()).toContain(expected)
    expect(wrapper.find('.legacy-area').exists()).toBe(legacy)
  }
  await router.push('/legacy/records/t1')
  await flushPromises()
  expect(wrapper.find('[data-evidence-id="DOC#1"]').exists()).toBe(true)
  wrapper.unmount()
})

test('pending judgement renders 승인/미승인 under the report bubble', async () => {
  const {default: InvestigationView} = await import('@/views/InvestigationView.vue')
  const {useInvestigationStore} = await import('@/stores/investigation')
  const {useIdentityStore} = await import('@/stores/identity')
  useIdentityStore().status = 'authenticated'
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

test('report renders physics, stages, approved history, and RAG citations', () => {
  const wrapper = mount(ReportView, {props:{report:{summary:'요약', demo:true,
    physicsResults:[{model:'etch_depth_constant_rate', version:'1.0', status:'calculated', formula:'D = R * t',
      inputs:[{key:'etch_rate_nm_min', value:500, unit:'nm/min', source:'user_input'}],
      result:{key:'expected_etch_depth_nm', value:1000, unit:'nm', source:'calculated'},
      assumptions:['속도 일정'], missing_fields:[], warnings:['실측값 아님']}],
    quantitativeResults:[{analysis:'metrology_comparison', version:'2.0', problem:'실측 깊이와 승인 규격 비교',
      status:'CALCULATED', value_origin:'CALCULATED', validation_status:'VALIDATED', formula:'error', inputs:[],
      results:[{key:'absolute_error', value:-80, unit:'nm', origin:'CALCULATED', source:'metrology'}],
      reference_ids:[], missing_fields:[], warnings:[], interpretation:'승인 관리 규격 범위를 벗어났습니다.'}],
    sensorAnalysis:{version:'2.0', problem:'센서 시계열 분석', status:'CALCULATED', target_run_id:'RUN-1',
      signals:[{sensor:'pressure_pv_mtorr', unit:'mTorr', minimum:25, maximum:31, mean:28,
        first_anomaly_sec:50, anomaly_duration_sec:20, cooccurring_sensors:['source_rf_reflected_w'],
        related_alarms:['PRESSURE_HIGH'], ocap_ids:['OCAP-ETCH-PRS'], threshold_source:'equipment_alarm'}],
      missing_fields:[], warnings:['인과관계 아님'], causal_conclusion:false},
    educationalSimulation:{version:'3.0', mode:'EDUCATIONAL_ASSUMPTION', status:'SIMULATED',
      validation_status:'NOT_VALIDATED', completed_levels:[1,2,3], source_run_id:'RUN-1', formulas:['AR = D/W'],
      coefficients:[{variable:'source_rf', value:0.35, unit:'per_relative_change', source:'교육용 가정', calibrated:false}],
      relative_rate_series:[{offset_sec:0, relative_rate:1.035, simulated_process_rate_nm_min:103.5, source:'mock_fab_sensor'}],
      profile_frames:[{offset_sec:60, depth_nm:95, opening_width_nm:80, aspect_ratio:1.1875,
        simulated_arde_rate_nm_min:89, removed_region:[{x_nm:-40,y_nm:0},{x_nm:40,y_nm:0},{x_nm:40,y_nm:95},{x_nm:-40,y_nm:95}]}],
      missing_fields:[], assumptions:['ARDE 계수는 교육용 가정'], warnings:['Bowing/Taper 미예측'], causal_conclusion:false},
    stages:[{key:'scope', title:'범위 조사 에이전트', status:'sample_based', agent_mode:'llm', findings:['사례 3건'], unknowns:['MES 미연결']}],
    history:[{id:'HIST-1', question:'과거 질문', summary:'과거 요약', causes:['RF'], approvedBy:'이엔지니어', approvedAt:'2026-10-12', lotId:'LOT-1'}],
    checks:[{title:'SOP-ETCH-12 · 4.2', rationale:'동시 비교', source:'rag_mcp', docId:'SOP-ETCH-12#4.2'}]}}})
  const text = wrapper.text()
  for (const expected of ['물리 계산 검증', '계산값: 1000.00 nm', '가정: 속도 일정', '주의: 실측값 아님',
    '고도화 정량 분석', 'absolute_error=-80.00 nm (CALCULATED)', '센서 시계열 정량 분석',
    '최초 이상 50.00초', '동반 이상: source_rf_reflected_w — 인과관계 아님',
    '교육용 식각 시뮬레이션 · 실제 조사 결과와 분리', 'SIMULATED · NOT_VALIDATED',
    '최종 가정 깊이 95.00 nm', 'Bowing/Taper 미예측',
    '조사 단계별 결과', '데모 사례 기반 · LLM 사용', '미확인: MES 미연결',
    '유사 승인 조사 이력', '과거 후보: RF', 'Lot LOT-1', 'SOP RAG 검색 결과 · 우선 확인 순서', '[SOP-ETCH-12#4.2]']) {
    expect(text).toContain(expected)
  }
  expect(wrapper.findAll('button.citation').map(button => button.text())).toContain('[SOP-ETCH-12#4.2]')
})
