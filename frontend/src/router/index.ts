import { createRouter, createWebHistory } from 'vue-router'
import InvestigationView from '@/views/InvestigationView.vue'
import RecordsView from '@/views/RecordsView.vue'
import SopView from '@/views/SopView.vue'

declare module 'vue-router' {
  interface RouteMeta { title: string }
}

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {path: '/', name: 'investigation', component: InvestigationView, meta: {title: '식각 장비 이상 조사'}},
    {path: '/records/:id?', name: 'records', component: RecordsView, meta: {title: '조사 기록'}},
    {path: '/sop/:id?', name: 'sop', component: SopView, meta: {title: 'SOP 목록'}},
    {path: '/:pathMatch(.*)*', redirect: '/'},
  ],
})
