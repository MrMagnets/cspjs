<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { setUnauthorizedHandler } from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const showFooter = computed(() => !route.meta.hideFooter)
const banned = computed(() => auth.user?.status === 'banned' && auth.user?.role !== 'admin')
const showBanOverlay = computed(() => banned.value && route.name !== 'appeals')

onMounted(async () => {
  if (auth.token) await auth.fetchMe()
  setUnauthorizedHandler(() => {
    auth.logout()
    ElMessage.warning('登录状态已失效，请重新登录')
    if (route.meta.requiresAuth) {
      router.push({ name: 'login', query: { redirect: route.fullPath } })
    }
  })
})

function goAppeal() {
  router.push({ name: 'appeals' })
}
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer v-if="showFooter" class="app-footer">
      <div class="footer-inner">
        <span>CSP 初赛训练系统</span>
      </div>
    </footer>

    <ConfirmDialog />

    <div v-if="showBanOverlay" class="ban-overlay">
      <div class="ban-card">
        <div class="ban-icon">!</div>
        <h1>您的账号已被封禁</h1>
        <p>当前账号存在严重违规行为，暂时无法继续使用站内功能。如对判定有异议，可提交录像链接进行申诉。</p>
        <el-button type="primary" size="large" @click="goAppeal">前往申诉中心</el-button>
        <span class="ban-tip">申诉通过后账号将自动恢复正常</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
}

.app-footer {
  border-top: 1px solid var(--border);
  background: #fff;
  padding: 20px 0;
  color: var(--muted);
  font-size: 13px;
}

.footer-inner {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.dot-sep {
  color: #c8d2dd;
}

.ban-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, .78);
  backdrop-filter: blur(8px);
}
.ban-card {
  width: min(520px, 100%);
  padding: 38px 34px;
  border-radius: 22px;
  background: #fff;
  text-align: center;
  box-shadow: 0 30px 80px rgba(0, 0, 0, .35);
}
.ban-icon {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: #fee2e2;
  color: #dc2626;
  font-size: 34px;
  font-weight: 900;
}
.ban-card h1 { margin: 0 0 10px; font-size: 24px; color: #111827; }
.ban-card p { color: #64748b; line-height: 1.8; margin: 0 0 22px; }
.ban-tip { display: block; margin-top: 14px; color: #94a3b8; font-size: 12px; }
</style>
