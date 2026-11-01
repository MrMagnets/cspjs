<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="page">
    <div class="card not-found">
      <p class="code">404</p>
      <p class="title">页面不存在</p>
      <p class="desc">链接可能已失效，或者题目尚未通过审核。</p>
      <div class="row" style="justify-content: center">
        <el-button @click="router.push({ name: 'home' })">返回首页</el-button>
        <el-button type="primary" @click="router.push({ name: 'problems' })">去题库</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  text-align: center;
  padding: 70px 20px;
}

.code {
  margin: 0;
  font-family: var(--mono);
  font-size: 54px;
  font-weight: 700;
  color: #d7e3e0;
  letter-spacing: 4px;
}

.title {
  margin: 8px 0 6px;
  font-size: 19px;
  font-weight: 700;
}

.desc {
  margin: 0 0 22px;
  color: var(--muted);
  font-size: 13.5px;
}
</style>
