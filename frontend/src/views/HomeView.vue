<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { problemApi, wrongApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import ProblemCard from '@/components/ProblemCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const auth = useAuthStore()

const latest = ref([])
const total = ref(0)
const loading = ref(true)
const dueCount = ref(0)
const wrongTotal = ref(0)

const entries = [
  {
    title: '题库浏览',
    desc: '按题型、标签、年份筛选',
    to: { name: 'problems' },
    mark: '题',
  },
  {
    title: '题单',
    desc: '按顺序逐题练习',
    to: { name: 'lists' },
    mark: '单',
  },
  {
    title: '错题本',
    desc: '间隔重复复习',
    to: { name: 'wrong-book' },
    mark: '错',
  },
  {
    title: '模拟考试',
    desc: '20 题，限时 120 分钟',
    to: { name: 'mock-exams' },
    mark: '考',
  },
]

onMounted(async () => {
  try {
    const page = await problemApi.list({ page_size: 6 })
    latest.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
  if (auth.isLoggedIn) {
    try {
      const count = await wrongApi.todayCount()
      dueCount.value = count.due
      wrongTotal.value = count.total
    } catch {
      /* 未登录或接口异常时静默 */
    }
  }
})
</script>

<template>
  <div class="page">
    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">CSP-J/S 第一轮认证</p>
        <h1>CSP-J/S 初赛训练</h1>
        <p class="hero-desc">覆盖单项选择、阅读程序、完善程序三类题型。</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push({ name: 'problems' })">
            开始训练
          </el-button>
          <el-button size="large" @click="router.push({ name: auth.isLoggedIn ? 'mock-exams' : 'login' })">
            模拟考试
          </el-button>
        </div>
        <div class="hero-meta">
          <span>{{ total }} 道题目</span>
        </div>
      </div>

      <aside class="review-card">
        <p class="rc-label">今日待复习</p>
        <p class="rc-num">
          {{ auth.isLoggedIn ? dueCount : '—' }}<small v-if="auth.isLoggedIn">题</small>
        </p>
        <p class="rc-desc">
          <template v-if="auth.isLoggedIn">共 {{ wrongTotal }} 道错题</template>
          <template v-else>登录后查看复习计划</template>
        </p>
        <el-button
          type="primary"
          plain
          class="rc-btn"
          @click="router.push(auth.isLoggedIn ? { name: 'wrong-book' } : { name: 'login' })"
        >
          {{ auth.isLoggedIn ? '去复习' : '登录查看' }}
        </el-button>
      </aside>
    </section>

    <section class="entries">
      <div v-for="entry in entries" :key="entry.title" class="entry" @click="router.push(entry.to)">
        <span class="entry-mark">{{ entry.mark }}</span>
        <div>
          <p class="entry-title">{{ entry.title }}</p>
          <p class="entry-desc">{{ entry.desc }}</p>
        </div>
      </div>
    </section>

    <section class="latest">
      <div class="page-title">
        最新题目
        <router-link :to="{ name: 'problems' }" class="more">查看全部 →</router-link>
      </div>
      <div v-loading="loading" class="problem-grid">
        <ProblemCard v-for="problem in latest" :key="problem.id" :problem="problem" />
      </div>
      <EmptyState
        v-if="!loading && !latest.length"
        title="题库还没有题目"
        description="登录后可投稿题目"
        action-text="去投稿"
        @action="router.push({ name: 'problem-create' })"
      />
    </section>
  </div>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 28px;
  align-items: stretch;
  padding: 34px 36px;
  border-radius: 18px;
  background: linear-gradient(135deg, #17564a 0%, #1f6f5c 48%, #2b8a72 100%);
  color: #fff;
  box-shadow: 0 12px 30px rgba(23, 86, 74, 0.22);
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12.5px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #cbe8dd;
}

.hero h1 {
  margin: 0 0 14px;
  font-size: 32px;
  line-height: 1.35;
  letter-spacing: 0.5px;
  font-weight: 700;
}

.hero-desc {
  margin: 0 0 22px;
  max-width: 560px;
  color: #d8ece4;
  font-size: 14.5px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-actions :deep(.el-button) {
  border-radius: 10px;
}

.hero-actions :deep(.el-button--primary) {
  background: #fff;
  border-color: #fff;
  color: var(--brand-dark);
  font-weight: 600;
}

.hero-actions :deep(.el-button--primary:hover) {
  background: #eef7f3;
  border-color: #eef7f3;
  color: var(--brand-dark);
}

.hero-actions :deep(.el-button:not(.el-button--primary)) {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.55);
  color: #fff;
}

.hero-actions :deep(.el-button:not(.el-button--primary):hover) {
  background: rgba(255, 255, 255, 0.12);
  border-color: #fff;
  color: #fff;
}

.hero-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 20px;
  font-size: 12.5px;
  color: #b9dccd;
}

.dot-sep {
  color: rgba(255, 255, 255, 0.4);
}

.review-card {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(4px);
}

.rc-label {
  margin: 0;
  font-size: 13px;
  color: #d8ece4;
}

.rc-num {
  margin: 6px 0 4px;
  font-size: 40px;
  font-weight: 700;
  line-height: 1.1;
  font-family: var(--mono);
}

.rc-num small {
  font-size: 14px;
  font-weight: 400;
  margin-left: 4px;
  color: #cbe8dd;
}

.rc-desc {
  margin: 0 0 16px;
  font-size: 12.5px;
  color: #cbe8dd;
  line-height: 1.7;
}

.rc-btn {
  margin-top: auto;
  background: rgba(255, 255, 255, 0.9) !important;
  border-color: transparent !important;
  color: var(--brand-dark) !important;
  font-weight: 600;
}

.entries {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 22px 0 30px;
}

@media (max-width: 1000px) {
  .entries {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.entry {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.entry:hover {
  border-color: #c3ded5;
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.entry-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border-radius: 10px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.entry-title {
  margin: 0 0 3px;
  font-size: 15px;
  font-weight: 650;
}

.entry-desc {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.6;
}

.latest .more {
  font-size: 13px;
  font-weight: 400;
}

.problem-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  min-height: 80px;
}

@media (max-width: 1000px) {
  .problem-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 26px 22px;
  }

  .hero h1 {
    font-size: 25px;
  }

  .problem-grid,
  .entries {
    grid-template-columns: 1fr;
  }
}
</style>
