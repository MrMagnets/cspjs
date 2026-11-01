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
const form = reactive({ username: '', password: '', confirm: '' })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3 - 50 个字符', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_\u4e00-\u9fa5-]+$/,
      message: '只能包含中英文、数字、下划线和连字符',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6 - 64 个字符', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const user = await auth.register(form.username.trim(), form.password)
    ElMessage.success(`注册成功，欢迎 ${user.username}`)
    router.replace('/')
  } catch (err) {
    ElMessage.error(err.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-head">
        <h1>注册</h1>
        <p>注册后即可投稿题目、创建题单、记录错题</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="3 - 50 个字符" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 6 位"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-button type="primary" class="auth-submit" :loading="loading" @click="submit">
          注册并登录
        </el-button>
      </el-form>

      <p class="auth-foot">
        已有账号？
        <router-link :to="{ name: 'login', query: route.query }">直接登录</router-link>
      </p>

      <p class="notice">
        密码经哈希后存储，平台不会保存明文。题目投稿需管理员审核后才会公开。
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

.notice {
  margin: 16px 0 0;
  font-size: 12px;
  line-height: 1.8;
  color: #8a99a8;
  text-align: center;
}
</style>
