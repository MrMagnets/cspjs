<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { confirm } = useConfirmDialog()

const navItems = computed(() => {
  const items = [
    { name: 'problems', label: '题库', to: { name: 'problems' } },
    { name: 'lists', label: '题单', to: { name: 'lists' } },
    { name: 'wrong-book', label: '错题本', to: { name: 'wrong-book' } },
    { name: 'mock-exams', label: '模拟考试', to: { name: 'mock-exams' } },
    { name: 'stats', label: '统计', to: { name: 'stats' } },
  ]
  if (auth.isAdmin) {
    items.push({ name: 'admin-review', label: '审核', to: { name: 'admin-review' } })
    items.push({ name: 'admin-tags', label: '标签', to: { name: 'admin-tags' } })
  }
  return items
})

const isActive = (to) => route.name === to.name

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
  if (command === 'submit') return router.push({ name: 'problem-create' })
  if (command === 'mine') return router.push({ name: 'my-problems' })
  if (command === 'review') return router.push({ name: 'admin-review' })
  if (command === 'tags') return router.push({ name: 'admin-tags' })
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link :to="{ name: 'home' }" class="brand">
        <span class="brand-mark">C</span>
        <span class="brand-text">
          <strong>CSP 初赛刷题</strong>
          <em>CCF CSP-J/S 第一轮认证</em>
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
          <el-button
            size="small"
            type="primary"
            plain
            class="submit-btn"
            @click="router.push({ name: 'problem-create' })"
          >
            投稿题目
          </el-button>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-chip">
              <span class="avatar">{{ auth.username.slice(0, 1).toUpperCase() }}</span>
              <span class="user-name">{{ auth.username }}</span>
              <span v-if="auth.isAdmin" class="role-badge">管理员</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="mine">我的投稿</el-dropdown-item>
                <el-dropdown-item command="submit">投稿新题目</el-dropdown-item>
                <template v-if="auth.isAdmin">
                  <el-dropdown-item command="review" divided>题目审核</el-dropdown-item>
                  <el-dropdown-item command="tags">标签管理</el-dropdown-item>
                </template>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button size="small" text @click="goLogin">登录</el-button>
          <el-button size="small" type="primary" @click="router.push({ name: 'register' })">
            注册
          </el-button>
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
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  height: 62px;
  display: flex;
  align-items: center;
  gap: 22px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  color: var(--text);
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand), #2f8f78);
  color: #fff;
  font-family: var(--mono);
  font-weight: 700;
  font-size: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px rgba(31, 111, 92, 0.25);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-text strong {
  font-size: 15.5px;
  letter-spacing: 0.3px;
}

.brand-text em {
  font-style: normal;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.2px;
}

.nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav::-webkit-scrollbar {
  display: none;
}

.nav-link {
  padding: 6px 12px;
  border-radius: 8px;
  color: #41525f;
  font-size: 14.5px;
  white-space: nowrap;
  transition: all 0.16s ease;
}

.nav-link:hover {
  background: #f0f4f7;
  color: var(--brand-dark);
}

.nav-link.active {
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  border: 1px solid var(--border);
  cursor: pointer;
  background: #fff;
  transition: all 0.16s ease;
}

.user-chip:hover {
  border-color: #b9d6cd;
  background: #fafdfc;
}

.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 700;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 13.5px;
  color: var(--text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-badge {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 999px;
  background: #fff4e9;
  color: #a2651a;
  border: 1px solid #f7e2cb;
}

@media (max-width: 860px) {
  .brand-text em {
    display: none;
  }

  .nav-link {
    padding: 6px 9px;
    font-size: 13.5px;
  }
}

@media (max-width: 720px) {
  .header-inner {
    gap: 12px;
    width: calc(100% - 24px);
  }

  .submit-btn {
    display: none;
  }

  .user-name {
    display: none;
  }

  .brand-text strong {
    font-size: 14px;
  }
}
</style>
