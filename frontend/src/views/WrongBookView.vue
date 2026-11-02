<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { wrongApi } from '@/api'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import MarkdownView from '@/components/MarkdownView.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ERROR_TYPE_OPTIONS, errorTypeLabel, formatDate } from '@/utils/format'

const router = useRouter()
const { confirm } = useConfirmDialog()

const TABS = [
  { name: 'due', label: '待复习' },
  { name: 'all', label: '全部错题' },
  { name: 'mastered', label: '已掌握' },
]

const loading = ref(true)
const items = ref([])
const scope = ref('due')
const counts = ref({ due: 0, total: 0, mastered: 0 })

const redoVisible = ref(false)
const redoLoading = ref(false)
const redo = ref(null)
const redoChoice = ref('')
const redoResult = ref(null)
const redoSubmitting = ref(false)

const masteredCount = computed(() => counts.value.mastered || 0)

async function loadCounts() {
  try {
    counts.value = await wrongApi.todayCount()
  } catch {
    /* 忽略 */
  }
}

async function load() {
  loading.value = true
  try {
    const data = await wrongApi.list({ scope: scope.value, limit: 100 })
    // 后端异常时可能返回 null / 非数组，必须归一化，否则模板空状态不渲染
    items.value = Array.isArray(data) ? data.filter((item) => item && item.id) : []
  } catch (err) {
    items.value = []
    ElMessage.error(err.message || '错题加载失败')
  } finally {
    loading.value = false
  }
}

async function switchScope(next) {
  if (scope.value === next) return
  scope.value = next
  await load()
}

async function setErrorType(item, value) {
  try {
    const updated = await wrongApi.setErrorType(item.id, value)
    item.error_type = updated.error_type
    ElMessage.success('错因已记录')
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  }
}

async function openRedo(item) {
  redoVisible.value = true
  redoLoading.value = true
  redo.value = null
  redoChoice.value = ''
  redoResult.value = null
  try {
    redo.value = await wrongApi.detail(item.id)
  } catch (err) {
    ElMessage.error(err.message || '题目加载失败')
    redoVisible.value = false
  } finally {
    redoLoading.value = false
  }
}

function normalize(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
}

async function submitRedo() {
  if (!redoChoice.value) {
    ElMessage.warning('请选择一个答案')
    return
  }
  redoSubmitting.value = true
  const isRight = normalize(redoChoice.value) === normalize(redo.value.sub_question.correct_answer)
  try {
    const updated = await wrongApi.review(redo.value.wrong_id, isRight ? 1 : 0)
    redoResult.value = {
      isRight,
      updated,
    }
    if (isRight) {
      ElMessage.success(
        updated.consecutive_pass >= 2 ? '连续答对两次，已标记为掌握并移出复习队列' : '回答正确，复习间隔已延长',
      )
    } else {
      ElMessage.warning('回答错误，明天再来复习一次')
    }
    await Promise.all([loadCounts(), load()])
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    redoSubmitting.value = false
  }
}

async function removeItem(item) {
  const ok = await confirm({
    title: '移出错题本',
    message: '移出后将不再出现在复习队列，确定吗？',
    confirmText: '移出',
    danger: true,
  })
  if (!ok) return
  try {
    await wrongApi.remove(item.id)
    ElMessage.success('已移出')
    await Promise.all([loadCounts(), load()])
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

function nextReviewText(item) {
  if (item.consecutive_pass >= 2) return '已掌握'
  if (!item.next_review_at) return '—'
  const next = new Date(item.next_review_at)
  const diff = next.getTime() - Date.now()
  if (diff <= 0) return '现在可以复习'
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
  return `${formatDate(item.next_review_at)}（约 ${days} 天后）`
}

onMounted(async () => {
  await Promise.all([load(), loadCounts()])
})
</script>

<template>
  <div class="page">
    <div class="page-title">
      错题本
      <span class="sub">
        待复习 {{ counts.due }} 题 · 共 {{ counts.total }} 题 · 已掌握 {{ masteredCount }} 题
      </span>
      <span class="spacer" />
      <el-button size="small" @click="router.push({ name: 'stats' })">查看统计</el-button>
    </div>

    <div class="rule-bar">
      <span class="rule-chip">首次做错 → 隔 1 天</span>
      <span class="rule-arrow">→</span>
      <span class="rule-chip">重做对 → 隔 3 天</span>
      <span class="rule-arrow">→</span>
      <span class="rule-chip">连续答对 2 次 → 已掌握</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in TABS"
        :key="tab.name"
        class="tab"
        :class="{ active: scope === tab.name }"
        @click="switchScope(tab.name)"
      >
        {{ tab.label }}
        <span class="tab-count">{{
          tab.name === 'due' ? counts.due : tab.name === 'all' ? counts.total : counts.mastered
        }}</span>
      </button>
    </div>

    <div v-loading="loading" class="wrong-list">
      <EmptyState
        v-if="!loading && !items.length"
        :title="scope === 'due' ? '今天没有待复习的错题' : scope === 'mastered' ? '还没有已掌握的错题' : '错题本还是空的'"
        description="做错的题目会自动进入错题本，并按 1 / 3 / 7 天的间隔安排复习。"
        action-text="去刷题"
        @action="router.push({ name: 'problems' })"
      />
      <article v-for="item in items" :key="item.id" class="wrong-item card">
        <div class="wi-head">
          <div class="wi-title-wrap">
            <router-link
              :to="{ name: 'problem-detail', params: { id: item.problem_id } }"
              class="wi-title"
            >
              {{ item.problem_title }}
            </router-link>
            <span class="type-badge" :class="item.problem_type">
              {{ item.problem_type === 'single' ? '单选' : item.problem_type === 'reading' ? '阅读程序' : '完善程序' }}
            </span>
            <span class="wi-order">第 {{ item.sub_question_order }} 小题</span>
          </div>
          <div class="wi-actions">
            <el-button size="small" type="primary" @click="openRedo(item)">重做</el-button>
            <el-button size="small" link type="danger" @click="removeItem(item)">移出</el-button>
          </div>
        </div>

        <div class="wi-content">
          <MarkdownView :content="item.sub_question_content || '（无小题题干）'" />
        </div>

        <div class="wi-foot">
          <div class="wi-field">
            <span class="wi-label">错因</span>
            <el-select
              :model-value="item.error_type"
              placeholder="标记错因"
              size="small"
              style="width: 132px"
              @update:model-value="(v) => setErrorType(item, v)"
            >
              <el-option
                v-for="option in ERROR_TYPE_OPTIONS"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <span v-if="item.error_type" class="wi-hint">{{ errorTypeLabel(item.error_type) }}</span>
          </div>

          <div class="wi-field">
            <span class="wi-label">连续答对</span>
            <span class="pass-dots">
              <span v-for="n in 2" :key="n" class="pass-dot" :class="{ on: item.consecutive_pass >= n }" />
            </span>
            <span class="wi-hint">{{ Math.min(item.consecutive_pass, 2) }} / 2</span>
          </div>

          <div class="wi-field">
            <span class="wi-label">下次复习</span>
            <span class="wi-hint">{{ nextReviewText(item) }}</span>
          </div>

          <span class="spacer" />
          <span class="wi-hint">已复习 {{ item.review_count }} 次</span>
        </div>
      </article>
    </div>

    <el-dialog v-model="redoVisible" title="错题重做" width="720px" top="6vh" align-center destroy-on-close>
      <div v-loading="redoLoading" class="redo-body">
        <template v-if="redo">
          <p class="redo-problem">{{ redo.problem_title }}</p>
          <div v-if="redo.problem_content_md" class="redo-context">
            <MarkdownView :content="redo.problem_content_md" />
          </div>

          <div class="redo-sub">
            <span class="sub-badge">{{ redo.sub_question.order_no }}</span>
            <div class="redo-sub-content">
              <MarkdownView :content="redo.sub_question.content_md || '请选择正确答案'" />
            </div>
          </div>

          <div class="redo-options">
            <div
              v-for="option in redo.sub_question.options"
              :key="option.key"
              class="option-item"
              :class="{
                active: redoChoice === option.key && !redoResult,
                correct: redoResult && String(redo.sub_question.correct_answer).includes(option.key),
                wrong:
                  redoResult && redoChoice === option.key && !String(redo.sub_question.correct_answer).includes(option.key),
              }"
              @click="!redoResult && (redoChoice = option.key)"
            >
              <span class="option-key">{{ option.key }}</span>
              <span class="option-text"><MarkdownView :content="option.text" /></span>
            </div>
          </div>

          <div v-if="redoResult" class="result-banner" :class="redoResult.isRight ? 'ok' : 'bad'">
            {{ redoResult.isRight ? '回答正确' : '回答错误' }}
            <span class="redo-answer">
              正确答案：{{ redo.sub_question.correct_answer }} · 连续答对
              {{ redoResult.updated.consecutive_pass }} 次
            </span>
          </div>

          <div v-if="redoResult && redo.sub_question.analysis_md" class="redo-analysis">
            <b>解析</b>
            <MarkdownView :content="redo.sub_question.analysis_md" />
          </div>
        </template>
      </div>

      <template #footer>
        <el-button v-if="redoResult" @click="redoVisible = false">关闭</el-button>
        <el-button v-if="redoResult" type="primary" plain @click="openRedo({ id: redo.wrong_id })">
          再来一次
        </el-button>
        <template v-if="!redoResult">
          <el-button @click="redoVisible = false">取消</el-button>
          <el-button type="primary" :loading="redoSubmitting" :disabled="!redoChoice" @click="submitRedo">
            提交答案
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rule-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 12.5px;
  color: var(--muted);
}

.rule-chip {
  background: var(--brand-soft);
  color: var(--brand-dark);
  padding: 2px 10px;
  border-radius: 999px;
}

.rule-arrow {
  color: #c8d2dd;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--border);
  background: #fff;
  color: #55697a;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13.5px;
  cursor: pointer;
}

.tab.active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}

.tab-count {
  font-family: var(--mono);
  font-size: 12px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 999px;
  padding: 0 6px;
}

.tab.active .tab-count {
  background: rgba(255, 255, 255, 0.22);
}

.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100px;
}

.wi-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.wi-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}

.wi-title {
  font-size: 15.5px;
  font-weight: 650;
  color: var(--text);
}

.wi-title:hover {
  color: var(--brand-dark);
}

.wi-order {
  font-size: 12px;
  color: var(--muted);
}

.wi-actions {
  display: flex;
  gap: 6px;
}

.wi-content {
  margin-top: 10px;
  padding: 12px 14px;
  background: #fcfdfe;
  border: 1px solid var(--border);
  border-radius: 9px;
}

.wi-foot {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--muted);
}

.wi-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wi-label {
  color: #7d8c9b;
}

.wi-hint {
  color: var(--muted);
}

.pass-dots {
  display: inline-flex;
  gap: 4px;
}

.pass-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e4e9f0;
}

.pass-dot.on {
  background: var(--ok);
}

.redo-body {
  max-height: 66vh;
  overflow-y: auto;
  min-height: 120px;
}

.redo-problem {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--muted);
}

.redo-context {
  padding: 12px 14px;
  background: #fcfdfe;
  border: 1px solid var(--border);
  border-radius: 9px;
  max-height: 220px;
  overflow-y: auto;
}

.redo-sub {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.redo-sub-content {
  flex: 1;
  min-width: 0;
}

.redo-options {
  margin: 12px 0 0 36px;
}

.option-text :deep(.markdown-body p) {
  margin: 0;
}

.redo-answer {
  margin-left: 10px;
  font-weight: 400;
}

.redo-analysis {
  margin-top: 14px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 9px;
  font-size: 13.5px;
}

.redo-analysis b {
  color: var(--brand-dark);
}
</style>
