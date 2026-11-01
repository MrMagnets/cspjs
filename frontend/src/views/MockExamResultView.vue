<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { mockApi } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'
import SubQuestionBlock from '@/components/SubQuestionBlock.vue'
import StatBar from '@/components/StatBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import { TYPE_LABELS, formatDate, formatDuration, percent } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const result = ref(null)

const examId = computed(() => Number(route.params.id))

const itemMap = computed(() => {
  const map = {}
  ;(result.value?.items || []).forEach((item) => {
    map[item.sub_question_id] = item
  })
  return map
})

const correctCount = computed(() => (result.value?.items || []).filter((i) => i.is_correct).length)
const totalCount = computed(() => (result.value?.items || []).length)

const scoreTone = computed(() => {
  const score = result.value?.score ?? 0
  if (score >= 80) return 'ok'
  if (score >= 60) return 'partial'
  return 'bad'
})

const scoreComment = computed(() => {
  const score = result.value?.score ?? 0
  if (score >= 90) return '稳扎稳打，冲刺高分'
  if (score >= 70) return '基础不错，注意细节与程序阅读'
  if (score >= 50) return '还有明显短板，按知识点专项突破'
  return '建议先系统复习基础语法与常见算法'
})

function problemStatus(problem) {
  const items = (problem.sub_questions || []).map((sub) => itemMap.value[sub.id]).filter(Boolean)
  if (!items.length) return { label: '未作答', class: 'warn' }
  if (items.every((item) => !item.user_answer)) return { label: '未作答', class: 'warn' }
  const right = items.filter((i) => i.is_correct).length
  if (right === items.length) return { label: '全部正确', class: 'ok' }
  if (right === 0) return { label: '全部错误', class: 'bad' }
  return { label: `答对 ${right}/${items.length}`, class: 'warn' }
}

onMounted(async () => {
  try {
    result.value = await mockApi.result(examId.value)
  } catch (err) {
    ElMessage.error(err.message || '成绩加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div v-if="loading" v-loading="true" class="card skeleton" />

    <template v-else-if="result">
      <div class="page-title">
        模拟考试结果
        <span class="sub">{{ result.exam_type === 'J' ? 'CSP-J' : 'CSP-S' }} 模拟卷 · {{ formatDate(result.started_at, true) }}</span>
        <span class="spacer" />
        <el-button size="small" @click="router.push({ name: 'mock-exams' })">返回模拟考试</el-button>
      </div>

      <section class="score-card card">
        <div class="score-main">
          <p class="sm-label">总分</p>
          <p class="sm-score" :class="scoreTone">{{ result.score }}<small> / 100</small></p>
          <p class="sm-comment">{{ scoreComment }}</p>
        </div>
        <div class="score-facts">
          <div class="fact">
            <p class="fact-value">{{ correctCount }} / {{ totalCount }}</p>
            <p class="fact-label">小题正确数</p>
          </div>
          <div class="fact">
            <p class="fact-value">{{ percent(totalCount ? correctCount / totalCount : 0, 1) }}</p>
            <p class="fact-label">小题正确率</p>
          </div>
          <div class="fact">
            <p class="fact-value">{{ formatDuration(result.duration_seconds) }}</p>
            <p class="fact-label">考试用时</p>
          </div>
          <div class="fact">
            <p class="fact-value">{{ result.submitted_at ? formatDate(result.submitted_at, true) : '—' }}</p>
            <p class="fact-label">交卷时间</p>
          </div>
        </div>
      </section>

      <div class="charts">
        <section class="card">
          <h2 class="block-title">题型得分率</h2>
          <StatBar
            v-for="item in result.by_type"
            :key="item.type"
            :label="TYPE_LABELS[item.type] || item.type"
            :total="item.total"
            :correct="item.correct"
            :accuracy="item.accuracy"
          />
          <p v-if="!result.by_type.length" class="muted empty-line">暂无分题型数据</p>
        </section>

        <section class="card">
          <h2 class="block-title">知识点得分率</h2>
          <StatBar
            v-for="item in result.by_tag"
            :key="item.name"
            :label="item.name"
            :total="item.total"
            :correct="item.correct"
            :accuracy="item.accuracy"
          />
          <p v-if="!result.by_tag.length" class="muted empty-line">题目未关联知识点标签</p>
        </section>
      </div>

      <section class="analysis-head card">
        <h2 class="block-title" style="margin: 0">逐题解析</h2>
        <span class="muted analysis-hint">绿色为正确答案，红色为你选错的选项</span>
      </section>

      <article v-for="(problem, index) in result.problems" :key="problem.id" class="card problem-block">
        <div class="pb-head">
          <span class="pb-index">第 {{ index + 1 }} 题</span>
          <span class="type-badge" :class="problem.type">{{ TYPE_LABELS[problem.type] }}</span>
          <span class="pb-status" :class="problemStatus(problem).class">
            {{ problemStatus(problem).label }}
          </span>
          <span class="spacer" />
          <router-link :to="{ name: 'problem-detail', params: { id: problem.id } }" class="pb-link">
            在题库中查看 →
          </router-link>
        </div>

        <h3 class="pb-title">{{ problem.title }}</h3>

        <div class="pb-content">
          <MarkdownView :content="problem.content_md" />
        </div>

        <SubQuestionBlock
          v-for="(sub, subIndex) in problem.sub_questions"
          :key="sub.id"
          :sub="sub"
          :index="subIndex + 1"
          :model-value="itemMap[sub.id]?.user_answer || ''"
          :result="itemMap[sub.id] || null"
          show-answer
          disabled
        />
      </article>

      <div class="bottom-actions">
        <el-button @click="router.push({ name: 'mock-exams' })">返回列表</el-button>
        <el-button type="primary" @click="router.push({ name: 'mock-exams' })">再考一套</el-button>
      </div>
    </template>

    <EmptyState
      v-else
      title="无法加载考试结果"
      description="考试可能尚未交卷，或者链接有误。"
      action-text="返回模拟考试"
      @action="router.push({ name: 'mock-exams' })"
    />
  </div>
</template>

<style scoped>
.skeleton {
  min-height: 220px;
}

.score-card {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 24px;
  padding: 26px 28px;
}

@media (max-width: 820px) {
  .score-card {
    grid-template-columns: 1fr;
  }
}

.score-main {
  border-right: 1px dashed var(--border);
  padding-right: 20px;
}

@media (max-width: 820px) {
  .score-main {
    border-right: none;
    border-bottom: 1px dashed var(--border);
    padding: 0 0 16px;
  }
}

.sm-label {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
}

.sm-score {
  margin: 4px 0 6px;
  font-size: 46px;
  font-weight: 700;
  font-family: var(--mono);
  line-height: 1.1;
}

.sm-score.ok {
  color: var(--ok);
}

.sm-score.partial {
  color: var(--warn);
}

.sm-score.bad {
  color: var(--bad);
}

.sm-score small {
  font-size: 14px;
  font-weight: 400;
  color: var(--muted);
}

.sm-comment {
  margin: 0;
  font-size: 13px;
  color: #55697a;
}

.score-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  align-content: center;
}

@media (max-width: 1000px) {
  .score-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.fact-value {
  margin: 0 0 3px;
  font-size: 17px;
  font-weight: 700;
  font-family: var(--mono);
  color: var(--text);
}

.fact-label {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .charts {
    grid-template-columns: 1fr;
  }
}

.block-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}

.empty-line {
  font-size: 13px;
  margin: 6px 0 0;
}

.analysis-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.analysis-hint {
  font-size: 12.5px;
}

.problem-block {
  margin-top: 14px;
  padding: 22px 24px;
}

.pb-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pb-index {
  font-family: var(--mono);
  font-size: 12.5px;
  background: #f2f5f8;
  color: #55697a;
  padding: 2px 10px;
  border-radius: 999px;
}

.pb-status {
  font-size: 12px;
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 600;
}

.pb-status.ok {
  background: var(--ok-soft);
  color: #1d7a52;
}

.pb-status.warn {
  background: var(--warn-soft);
  color: #96690f;
}

.pb-status.bad {
  background: var(--bad-soft);
  color: #a33b38;
}

.pb-link {
  font-size: 12.5px;
}

.pb-title {
  margin: 10px 0 12px;
  font-size: 18px;
}

.pb-content {
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}

.bottom-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin: 28px 0 10px;
}
</style>
