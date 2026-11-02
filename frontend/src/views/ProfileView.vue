<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import UserTitle from '@/components/UserTitle.vue'

const auth = useAuthStore()
const newUsername = ref('')
const avatarInput = ref('')
const saving = ref(false)
const avatarSaving = ref(false)
const loading = ref(true)
const now = ref(Date.now())
let timer = null

const COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000

const isAdmin = computed(() => auth.user?.role === 'admin')
const isBanned = computed(() => auth.user?.status === 'banned')
const lastChangeAt = computed(() => {
  const raw = auth.user?.last_username_change
  return raw ? new Date(raw).getTime() : 0
})
const nextChangeAt = computed(() => (lastChangeAt.value ? lastChangeAt.value + COOLDOWN_MS : 0))
const cooldownDays = computed(() => {
  if (!nextChangeAt.value || nextChangeAt.value <= now.value) return 0
  return Math.ceil((nextChangeAt.value - now.value) / (24 * 60 * 60 * 1000))
})
const canChange = computed(() => !isBanned.value && (isAdmin.value || cooldownDays.value === 0))

const cooldownText = computed(() => {
  if (isAdmin.value) return '管理员无冷却限制'
  if (cooldownDays.value > 0) return `距离下次改名还剩 ${cooldownDays.value} 天`
  return '当前可以修改用户名'
})

const lastChangeText = computed(() => {
  if (!lastChangeAt.value) return '从未修改过'
  return new Date(lastChangeAt.value).toLocaleString('zh-CN', { hour12: false })
})

const avatarUrl = computed(() =>
  auth.user?.avatar_url && auth.user?.avatar_status === 'approved' ? auth.user.avatar_url : '',
)
const avatarStatusText = computed(() => {
  if (!auth.user?.avatar_url) return '未设置'
  return { pending: '审核中', approved: '已通过', rejected: '未通过' }[auth.user.avatar_status] || '未知'
})

async function submitAvatar() {
  const url = avatarInput.value.trim()
  if (!/^https?:\/\//.test(url)) {
    ElMessage.warning('头像链接必须以 http(s):// 开头')
    return
  }
  avatarSaving.value = true
  try {
    await userApi.updateAvatar(url)
    await auth.fetchMe()
    avatarInput.value = ''
    ElMessageBox.alert(
      isAdmin.value ? '头像已更新。' : '头像已提交，管理员审核通过后生效。',
      '提交成功',
      { type: 'success' },
    )
  } catch (err) {
    ElMessage.error(err.message || '头像提交失败')
  } finally {
    avatarSaving.value = false
  }
}

function fmtDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('zh-CN')
}

async function submit() {
  const name = newUsername.value.trim()
  if (name.length < 3 || name.length > 20) {
    ElMessage.warning('用户名长度需为 3–20 个字符')
    return
  }
  if (!/^[A-Za-z0-9_\u4e00-\u9fa5-]+$/.test(name)) {
    ElMessage.warning('用户名只能包含中文、字母、数字、下划线或短横线')
    return
  }
  if (name === auth.user?.username) {
    ElMessage.warning('新用户名与当前用户名相同')
    return
  }

  saving.value = true
  try {
    const result = await userApi.changeName(name)
    // 刷新 Pinia 全局用户状态，右上角用户名立即更新
    await auth.fetchMe()
    newUsername.value = ''
    await ElMessageBox.alert(
      `用户名已修改为「${result.user.username}」。普通用户 30 天内只能修改一次。`,
      '修改成功',
      { type: 'success', confirmButtonText: '知道了' },
    )
  } catch (err) {
    ElMessage.error(err.message || '修改失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    if (auth.token) await auth.fetchMe()
  } finally {
    loading.value = false
    now.value = Date.now()
    timer = setInterval(() => {
      now.value = Date.now()
    }, 60 * 1000)
  }
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="page profile-page">
    <div class="page-title">
      个人中心
      <span class="sub">账号信息 · 用户名管理</span>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />
    <template v-else-if="auth.user">
      <section class="profile-hero">
        <div class="hero-avatar" :class="{ brown: isBanned }">
          <img v-if="avatarUrl" :src="avatarUrl" alt="avatar" />
          <template v-else>{{ auth.user.username.slice(0, 1).toUpperCase() }}</template>
        </div>
        <div class="hero-main">
          <div class="hero-name-row">
            <h1 :class="{ brown: isBanned }">{{ auth.user.username }}</h1>
            <UserTitle :user="auth.user" />
          </div>
          <p class="hero-meta">
            注册于 {{ fmtDate(auth.user.created_at) }} · 上次改名：{{ lastChangeText }}
          </p>
        </div>
        <div class="hero-score">
          <span>{{ auth.user.monkey_score }}</span>
          <small>小猴值</small>
        </div>
      </section>

      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-label">小猴值</span>
          <strong>{{ auth.user.monkey_score }}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-label">信用分</span>
          <strong :class="{ danger: auth.user.credit_score < 100 }">{{ auth.user.credit_score }}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-label">账号状态</span>
          <el-tag :type="isBanned ? 'danger' : 'success'" effect="dark" size="large">
            {{ isBanned ? '已封禁' : '正常' }}
          </el-tag>
        </div>
      </div>

      <el-card shadow="never" class="rename-card avatar-card">
        <template #header>
          <div class="card-head">
            <div>
              <strong>头像</strong>
              <p>支持外链图片；普通用户提交后需管理员审核，管理员直接生效。</p>
            </div>
            <el-tag :type="auth.user.avatar_status === 'approved' ? 'success' : 'warning'" effect="plain">
              {{ avatarStatusText }}
            </el-tag>
          </div>
        </template>
        <div class="avatar-form">
          <el-input v-model="avatarInput" placeholder="https://example.com/avatar.png" clearable />
          <el-button type="primary" :loading="avatarSaving" @click="submitAvatar">提交头像</el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="rename-card">
        <template #header>
          <div class="card-head">
            <div>
              <strong>修改用户名</strong>
              <p>用户名会显示在排行榜、讨论区和提交记录中。</p>
            </div>
            <el-tag :type="canChange ? 'success' : 'warning'" effect="plain">{{ cooldownText }}</el-tag>
          </div>
        </template>

        <el-alert
          v-if="isAdmin"
          type="success"
          :closable="false"
          show-icon
          title="你是管理员：无 30 天冷却限制，可随时修改。"
          class="tip"
        />
        <el-alert
          v-else-if="cooldownDays > 0"
          type="warning"
          :closable="false"
          show-icon
          :title="`距离下次改名还剩 ${cooldownDays} 天，冷却期内无法修改。`"
          class="tip"
        />
        <el-alert
          v-else
          type="info"
          :closable="false"
          show-icon
          title="普通用户每 30 天可修改一次用户名，修改后立即生效。"
          class="tip"
        />
        <el-alert
          v-if="isBanned"
          type="error"
          :closable="false"
          show-icon
          title="账号处于封禁状态，无法修改用户名；请先在申诉中心提交申诉。"
          class="tip"
        />

        <el-form label-position="top" class="rename-form" @submit.prevent="submit">
          <el-form-item label="新用户名">
            <el-input
              v-model="newUsername"
              :disabled="!canChange || saving"
              maxlength="20"
              minlength="3"
              show-word-limit
              placeholder="3–20 个字符，支持中文 / 字母 / 数字 / _ / -"
              clearable
            />
          </el-form-item>
          <div class="form-foot">
            <span class="hint">修改成功后，排行榜、讨论区与 Header 会同步更新。</span>
            <el-button
              type="primary"
              :loading="saving"
              :disabled="!canChange || !newUsername.trim()"
              @click="submit"
            >
              确认修改
            </el-button>
          </div>
        </el-form>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.profile-page { max-width: 880px; margin: 0 auto; }
.profile-hero {
  display: flex; align-items: center; gap: 20px; padding: 26px;
  border-radius: 20px; background: linear-gradient(135deg, #f8fbff, #eef4ff 60%, #e8f0ff);
  border: 1px solid #dbe7ff;
}
.hero-avatar {
  display: grid; place-items: center; width: 76px; height: 76px; border-radius: 22px;
  background: linear-gradient(135deg, #1d4ed8, #60a5fa); color: #fff; font-size: 32px; font-weight: 800;
  box-shadow: 0 12px 28px rgba(37, 99, 235, .25); overflow: hidden; flex: none;
}
.hero-avatar img { width: 100%; height: 100%; object-fit: cover; }
.hero-avatar.brown { background: linear-gradient(135deg, #7a4a1d, #b0895f); }
.hero-main { flex: 1; min-width: 0; }
.hero-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.hero-name-row h1 { margin: 0; font-size: 26px; }
.hero-name-row h1.brown { color: #8b5a2b; }
.hero-meta { margin: 6px 0 0; color: var(--muted); font-size: 12px; }
.hero-score { text-align: right; }
.hero-score span { display: block; font-size: 34px; font-weight: 800; color: var(--accent); }
.hero-score small { color: var(--muted); font-size: 12px; }
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 16px 0; }
.stat-card { padding: 16px 18px; border-radius: 14px; border: 1px solid var(--border); background: #fff; display: flex; flex-direction: column; gap: 8px; }
.stat-label { color: var(--muted); font-size: 12px; }
.stat-card strong { font-size: 24px; }
.stat-card strong.danger { color: #dc2626; }
.rename-card { border-radius: 16px; }
.avatar-card { margin-bottom: 16px; }
.avatar-form { display: flex; gap: 10px; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card-head p { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.tip { margin-bottom: 12px; border-radius: 10px; }
.rename-form { margin-top: 6px; }
.form-foot { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.hint { color: var(--muted); font-size: 12px; }
@media (max-width: 680px) {
  .profile-hero { flex-wrap: wrap; }
  .stat-grid { grid-template-columns: 1fr; }
  .form-foot { align-items: flex-start; flex-direction: column; }
}
</style>
