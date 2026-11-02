<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import UserTitle from '@/components/UserTitle.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { confirm } = useConfirmDialog()

const navItems = computed(() => {
  const items = [
    { name: 'problems', label: '题库', to: { name: 'problems' } },
    { name: 'contests', label: '比赛', to: { name: 'contests' } },
    { name: 'discussions', label: '讨论', to: { name: 'discussions' } },
    { name: 'rankings', label: '排行榜', to: { name: 'rankings' } },
    { name: 'lists', label: '题单', to: { name: 'lists' } },
    { name: 'wrong-book', label: '错题本', to: { name: 'wrong-book' } },
    { name: 'mock-exams', label: '模拟考试', to: { name: 'mock-exams' } },
    { name: 'stats', label: '统计', to: { name: 'stats' } },
  ]
  if (auth.isAdmin) {
    items.push({ name: 'admin-users', label: '用户管理', to: { name: 'admin-users' } })
    items.push({ name: 'admin-review', label: '审核', to: { name: 'admin-review' } })
    items.push({ name: 'admin-tags', label: '标签', to: { name: 'admin-tags' } })
  }
  return items
})

const isActive = (to) => route.name === to.name
const brown = computed(() => /作弊|棕名/.test(auth.user?.title || ''))
const avatarUrl = computed(() =>
  auth.user?.avatar_url && auth.user?.avatar_status === 'approved' ? auth.user.avatar_url : '',
)

async function handleLogout() {
  const ok = await confirm({
    title: '退出登录',
    message: '确定要退出当前账号吗？',
    confirmText: '退出',
  })
  if (!ok) return
  auth.logout()
  ElMessage.success('已退出登录')
  router.push({ name: 'home' })
}

function onCommand(command) {
  if (command === 'logout') return handleLogout()
  if (command === 'profile') return router.push({ name: 'profile' })
  if (command === 'submit') return router.push({ name: 'problem-create' })
  if (command === 'mine') return router.push({ name: 'my-problems' })
  if (command === 'appeals') return router.push({ name: 'appeals' })
  if (command === 'review') return router.push({ name: 'admin-review' })
  if (command === 'tags') return router.push({ name: 'admin-tags' })
  if (command === 'users') return router.push({ name: 'admin-users' })
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link :to="{ name: 'home' }" class="brand">
        <img class="brand-mark" src="/icon/icon-192.png" alt="CSP 初赛训练系统" width="34" height="34" />
        <span class="brand-text">
          <strong>CSP 初赛训练系统</strong>
          <em>CSP-J/S 刷题平台</em>
        </span>
      </router-link>

      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          class="nav-link"
          :class="{ active: isActive(item.to) }"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="header-right">
        <template v-if="auth.isLoggedIn">
          <el-button size="small" type="primary" plain class="submit-btn" @click="router.push({ name: 'problem-create' })">
            投稿题目
          </el-button>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-chip" :class="{ 'is-brown': brown }">
              <span class="avatar">
                <img v-if="avatarUrl" :src="avatarUrl" alt="avatar" />
                <template v-else>{{ auth.username.slice(0, 1).toUpperCase() }}</template>
              </span>
              <span class="user-name">{{ auth.username }}</span>
              <UserTitle :user="auth.user" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="mine">我的投稿</el-dropdown-item>
                <el-dropdown-item command="submit">投稿新题</el-dropdown-item>
                <el-dropdown-item command="appeals">申诉中心</el-dropdown-item>
                <template v-if="auth.isAdmin">
                  <el-dropdown-item command="users" divided>用户管理</el-dropdown-item>
                  <el-dropdown-item command="review">题目审核</el-dropdown-item>
                  <el-dropdown-item command="tags">标签管理</el-dropdown-item>
                </template>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button size="small" text @click="goLogin">登录</el-button>
          <el-button size="small" type="primary" @click="router.push({ name: 'register' })">注册</el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
}
.header-inner {
  width: min(1320px, calc(100% - 40px));
  margin: 0 auto;
  height: 62px;
  display: flex;
  align-items: center;
  gap: 18px;
}
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; flex: none; }
.brand-mark { border-radius: 9px; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text strong { font-size: 15px; color: var(--text-strong); letter-spacing: .2px; }
.brand-text em { font-style: normal; font-size: 10px; color: var(--muted); }
.nav { display: flex; align-items: center; gap: 2px; margin-left: 4px; overflow: hidden; }
.nav-link {
  padding: 7px 10px;
  border-radius: 8px;
  color: var(--muted);
  font-size: 13px;
  text-decoration: none;
  white-space: nowrap;
  transition: background .18s, color .18s;
}
.nav-link:hover { color: var(--text-strong); background: #f3f6fb; }
.nav-link.active { color: #1d4ed8; background: #eef4ff; font-weight: 600; }
.header-right { margin-left: auto; display: flex; align-items: center; gap: 10px; flex: none; }
.submit-btn { border-radius: 8px; }
.user-chip { display: inline-flex; align-items: center; gap: 7px; cursor: pointer; padding: 4px 8px; border-radius: 999px; background: #f7f9fd; }
.user-chip.is-brown { background: #f3e7da; }
.avatar { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: #1d4ed8; color: #fff; font-size: 12px; font-weight: 700; overflow: hidden; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.user-chip.is-brown .avatar { background: #8b5a2b; }
.user-name { font-size: 13px; color: var(--text-strong); max-width: 110px; overflow: hidden; text-overflow: ellipsis; }
.user-chip.is-brown .user-name { color: #8b5a2b; font-weight: 700; }
.role-badge { font-size: 10px; padding: 1px 6px; border-radius: 999px; background: #e0edff; color: #1d4ed8; }
.brown-badge { background: #8b5a2b; color: #fff; }
@media (max-width: 1200px) { .nav-link { padding: 6px; font-size: 12px; } .brand-text em { display: none; } }
@media (max-width: 900px) { .brand-text { display: none; } .submit-btn { display: none; } }
</style>
