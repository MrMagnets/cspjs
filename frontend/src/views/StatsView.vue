<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { statsApi } from '@/api'
import StatBar from '@/components/StatBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import { TYPE_LABELS, percent } from '@/utils/format'

const router = useRouter()
const loading = ref(true)
const stats = ref(null)

const typeStats = computed(() =>
  (stats.value?.by_type || []).map((item) => ({ ...item, label: TYPE_LABELS[item.type] || item.type })),
)

const tagStats = computed(() => stats.value?.by_tag || [])
const hasData = computed(() => (stats.value?.total_answers || 0) > 0)

const cards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '累计作答', value: s.total_answers, suffix: '题', hint: '不含模拟考试' },
    { label: '整体正确率', value: percent(s.accuracy, 1), suffix: '', hint: `${s.correct_answers} 题正确` },
    { label: '今日作答', value: s.today_answers, suffix: '题', hint: '按 UTC 自然日统计' },
    { label: '做对题目', value: s.solved_problems, suffix: '道', hint: '去重后的题目数' },
    { label: '待复习错题', value: s.wrong_pending, suffix: '题', hint: '尚未掌握' },
  ]
})

onMounted(async () => {
  try {
    stats.value = await statsApi.me()
  } catch (err) {
    ElMessage.error(err.message || '统计加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="page-title">
      做题统计
      <span class="sub">数据来自普通练习记录，模拟考试成绩单独统计</span>
      <span class="spacer" />
      <el-button size="small" @click="router.push({ name: 'mock-exams' })">去模拟考试</el-button>
    </div>

    <div v-loading="loading">
      <div class="stat-cards">
        <div v-for="card in cards" :key="card.label" class="stat-card card">
          <p class="sc-label">{{ card.label }}</p>
          <p class="sc-value">
            {{ card.value }}<small v-if="card.suffix">{{ card.suffix }}</small>
          </p>
          <p class="sc-hint">{{ card.hint }}</p>
        </div>
      </div>

      <div v-if="hasData" class="charts">
        <section class="card">
          <h2 class="block-title">题型维度正确率</h2>
          <StatBar
            v-for="item in typeStats"
            :key="item.type"
            :label="item.label"
            :total="item.total"
            :correct="item.correct"
            :accuracy="item.accuracy"
          />
          <p v-if="!typeStats.length" class="muted empty-line">还没有分题型的作答记录</p>
        </section>

        <section class="card">
          <h2 class="block-title">知识点维度正确率</h2>
          <StatBar
            v-for="item in tagStats"
            :key="item.name"
            :label="item.name"
            :total="item.total"
            :correct="item.correct"
            :accuracy="item.accuracy"
          />
          <p v-if="!tagStats.length" class="muted empty-line">
            题目还没有关联知识点标签，或该维度暂无作答记录
          </p>
        </section>
      </div>

      <EmptyState
        v-if="!loading && !hasData"
        title="还没有做题记录"
        description="完成任意一道题的作答后，这里会展示题型与知识点维度的正确率。"
        action-text="去刷题"
        @action="router.push({ name: 'problems' })"
      />
    </div>
  </div>
</template>

<style scoped>
.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

@media (max-width: 1000px) {
  .stat-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.stat-card {
  padding: 16px 18px;
}

.sc-label {
  margin: 0 0 6px;
  font-size: 12.5px;
  color: var(--muted);
}

.sc-value {
  margin: 0 0 4px;
  font-size: 26px;
  font-weight: 700;
  font-family: var(--mono);
  color: var(--text);
  line-height: 1.2;
}

.sc-value small {
  font-size: 12px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 3px;
}

.sc-hint {
  margin: 0;
  font-size: 12px;
  color: #8a99a8;
}

.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 900px) {
  .charts {
    grid-template-columns: 1fr;
  }
}

.block-title {
  margin: 0 0 12px;
  font-size: 16.5px;
  font-weight: 700;
}

.empty-line {
  font-size: 13px;
  margin: 8px 0 0;
}
</style>
