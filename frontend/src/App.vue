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

onMounted(() => {
  setUnauthorizedHandler(() => {
    auth.logout()
    ElMessage.warning('登录状态已失效，请重新登录')
    if (route.meta.requiresAuth) {
      router.push({ name: 'login', query: { redirect: route.fullPath } })
    }
  })
})
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
        <span>CSP 初赛刷题 · 面向 CCF CSP-J/S 第一轮认证</span>
        <span class="dot-sep">·</span>
        <span>题目由社区贡献，管理员审核后进入公共题库</span>
        <span class="dot-sep">·</span>
        <span>刷题数据仅供自测参考</span>
      </div>
    </footer>

    <ConfirmDialog />
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
</style>
