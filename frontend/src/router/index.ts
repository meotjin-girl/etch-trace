import { createRouter, createWebHistory } from 'vue-router'
import AlarmLogView from '@/views/AlarmLogView.vue'
import ProposalView from '@/views/ProposalView.vue'
import CandidateView from '@/views/CandidateView.vue'
import ActionReviewView from '@/views/ActionReviewView.vue'
import ActionRecordView from '@/views/ActionRecordView.vue'
import InvestigationRecordsView from '@/views/InvestigationRecordsView.vue'
import SopView from '@/views/SopView.vue'
import InvestigationView from '@/views/InvestigationView.vue'
import RecordsView from '@/views/RecordsView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    title: string
    /** Sidebar section to highlight. */
    section?: 'alarms' | 'records' | 'sop'
    /** Previous question-first workspace, kept off the menu at /legacy. */
    legacy?: boolean
  }
}

const investigation = '/investigations/:id'
export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {path:'/', name:'alarms', component:AlarmLogView, meta:{title:'이상 로그', section:'alarms'}},
    {path:investigation, name:'proposal', component:ProposalView, meta:{title:'조사 제안서', section:'alarms'}},
    {path:`${investigation}/candidates/:cid`, name:'candidate', component:CandidateView, meta:{title:'원인 후보 상세', section:'alarms'}},
    {path:`${investigation}/action`, name:'action-review', component:ActionReviewView, meta:{title:'조치 검토', section:'alarms'}},
    {path:`${investigation}/record`, name:'action-record', component:ActionRecordView, meta:{title:'조치 기록', section:'alarms'}},
    {path:'/records/:id?', name:'records', component:InvestigationRecordsView, meta:{title:'조사 기록', section:'records'}},
    {path:'/sop/:id?', name:'sop', component:SopView, meta:{title:'SOP · OCAP', section:'sop'}},
    {path:'/legacy', name:'investigation', component:InvestigationView, meta:{title:'기존 작업 조사', legacy:true}},
    {path:'/legacy/records/:id?', name:'legacy-records', component:RecordsView, meta:{title:'기존 작업 기록', legacy:true}},
    {path:'/:pathMatch(.*)*', redirect:'/'},
  ],
})
