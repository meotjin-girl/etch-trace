import { createRouter, createWebHistory } from 'vue-router'
import { session, ROLES } from './api'
import LoginView from './views/LoginView.vue'
import WorkerView from './views/WorkerView.vue'
import EngineerView from './views/EngineerView.vue'
import AdminView from './views/AdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: LoginView },
    { path: '/worker', component: WorkerView, meta: { role: 'worker' } },
    { path: '/engineer/:id?', component: EngineerView, meta: { role: 'engineer' } },
    { path: '/admin', component: AdminView, meta: { role: 'admin' } },
  ],
})

// 역할별 화면 분리: 다른 역할의 화면으로 가면 자기 홈으로 돌려보냄 (실제 권한 검사는 서버)
router.beforeEach((to) => {
  if (!to.meta.role) return session.role ? ROLES[session.role].home : true
  if (!session.role) return '/'
  if (to.meta.role !== session.role) return ROLES[session.role].home
})

export default router
