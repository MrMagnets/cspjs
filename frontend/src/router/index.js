import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册', guestOnly: true },
  },
  {
    path: '/problems',
    name: 'problems',
    component: () => import('@/views/ProblemsView.vue'),
    meta: { title: '题库' },
  },
  {
    path: '/problems/new',
    name: 'problem-create',
    component: () => import('@/views/ProblemEditView.vue'),
    meta: { title: '投稿题目', requiresAuth: true },
  },
  {
    path: '/problems/:id',
    name: 'problem-detail',
    component: () => import('@/views/ProblemDetailView.vue'),
    meta: { title: '题目详情' },
  },
  {
    path: '/problems/:id/edit',
    name: 'problem-edit',
    component: () => import('@/views/ProblemEditView.vue'),
    meta: { title: '编辑题目', requiresAuth: true },
  },
  {
    path: '/my/problems',
    name: 'my-problems',
    component: () => import('@/views/MyProblemsView.vue'),
    meta: { title: '我的投稿', requiresAuth: true },
  },
  {
    path: '/admin/review',
    name: 'admin-review',
    component: () => import('@/views/AdminReviewView.vue'),
    meta: { title: '题目审核', requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/tags',
    name: 'admin-tags',
    component: () => import('@/views/TagsAdminView.vue'),
    meta: { title: '标签管理', requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/lists',
    name: 'lists',
    component: () => import('@/views/ListsView.vue'),
    meta: { title: '题单' },
  },
  {
    path: '/lists/:id',
    name: 'list-detail',
    component: () => import('@/views/ListDetailView.vue'),
    meta: { title: '题单详情' },
  },
  {
    path: '/wrong-book',
    name: 'wrong-book',
    component: () => import('@/views/WrongBookView.vue'),
    meta: { title: '错题本', requiresAuth: true },
  },
  {
    path: '/stats',
    name: 'stats',
    component: () => import('@/views/StatsView.vue'),
    meta: { title: '做题统计', requiresAuth: true },
  },
  {
    path: '/mock-exams',
    name: 'mock-exams',
    component: () => import('@/views/MockExamView.vue'),
    meta: { title: '模拟考试', requiresAuth: true },
  },
  {
    path: '/mock-exams/:id',
    name: 'mock-exam-run',
    component: () => import('@/views/MockExamView.vue'),
    meta: { title: '模拟考试进行中', requiresAuth: true },
  },
  {
    path: '/mock-exams/:id/result',
    name: 'mock-exam-result',
    component: () => import('@/views/MockExamResultView.vue'),
    meta: { title: '模拟考试结果', requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, savedPosition) => savedPosition || { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (auth.token && !auth.user) {
    await auth.fetchMe()
  }
  if (!auth.token) auth.ready = true

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    ElMessage.warning('该页面仅管理员可访问')
    return { name: 'home' }
  }
  if (to.meta.guestOnly && auth.isLoggedIn) {
    return { name: 'home' }
  }
  document.title = to.meta.title ? `${to.meta.title} · CSP 初赛训练系统` : 'CSP 初赛训练系统'
  return true
})

export default router
