<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const user = await auth.login(form.username.trim(), form.password)
    ElMessage.success(`欢迎回来，${user.username}`)
    const redirect = route.query.redirect
    router.replace(typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/')
  } catch (err) {
    ElMessage.error(err.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-head">
        <h1>登录</h1>
        <p>账号登录</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </el-form-item>
        <el-button type="primary" class="auth-submit" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>

      <p class="auth-foot">
        还没有账号？
        <router-link :to="{ name: 'register', query: route.query }">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 200px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
}

.auth-card {
  width: min(420px, 100%);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(31, 45, 61, 0.08);
  padding: 32px 30px 26px;
}

.auth-head {
  margin-bottom: 22px;
}

.auth-head h1 {
  margin: 0 0 6px;
  font-size: 23px;
  letter-spacing: 0.5px;
}

.auth-head p {
  margin: 0;
  color: var(--muted);
  font-size: 13.5px;
}

.auth-submit {
  width: 100%;
  margin-top: 6px;
  height: 42px;
  font-size: 15px;
}

.auth-foot {
  margin: 18px 0 0;
  text-align: center;
  font-size: 13.5px;
  color: var(--muted);
}
</style>
