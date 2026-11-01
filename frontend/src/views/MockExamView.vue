<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { mockApi } from '@/api'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import MarkdownView from '@/components/MarkdownView.vue'
import SubQuestionBlock from '@/components/SubQuestionBlock.vue'
import EmptyState from '@/components/EmptyState.vue'
import { TYPE_LABELS, formatDate, formatDuration, mockProblemPoints } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const { confirm } = useConfirmDialog()

const running = computed(() => Boolean(route.params.id))
const examId = computed(() => Number(route.params.id))

// ---------------- 开始页 ----------------
const examType = ref('J')
const starting = ref(false)
const history = ref([])
const historyLoading = ref(false)

const STRUCTURE = [
  { label: '单项选择', count: 15, score: 30, desc: '每题 2 分' },
  { label: '阅读程序', count: 3, score: 40, desc: '3 小题，按小题均分' },
  { label: '完善程序', count: 2, score: 30, desc: '5 小题，按小题均分' },
]

// ---------------- 考试中 ----------------
const loading = ref(false)
const exam = ref(null)
const answers = reactive({})
const currentIndex = ref(0)
const remaining = ref(0)
const submitting = ref(false)
const submitted = ref(false)
let timer = null

const draftKey = computed(() => `cspjs_mock_draft_${examId.value}`)

const problems = computed(() => exam.value?.problems || [])
const currentProblem = computed(() => problems.value[currentIndex.value] || null)

const sections = computed(() => {
  const list = [
    { title: '一、单项选择（1 - 15）', range: [0, 15] },
    { title: '二、阅读程序（16 - 18）', range: [15, 18] },
    { title: '三、完善程序（19 - 20）', range: [18, 20] },
  ]
  return list
    .map((section) => ({
      ...section,
      items: problems.value.slice(section.range[0], section.range[1]).map((problem, idx) => ({
        problem,
        index: section.range[0] + idx,
      })),
    }))
    .filter((section) => section.items.length)
})

const totalSubs = computed(() =>
  problems.value.reduce((sum, problem) => sum + (problem.sub_questions?.length || 0), 0),
)

const answeredSubs = computed(() => {
  let count = 0
  problems.value.forEach((problem) => {
    ;(problem.sub_questions || []).forEach((sub) => {
      if (answers[sub.id]) count += 1
    })
  })
  return count
})

const timerTone = computed(() => (remaining.value <= 600 ? 'danger' : 'normal'))

function problemAnswered(problem) {
  return (problem.sub_questions || []).some((sub) => Boolean(answers[sub.id]))
}

function problemComplete(problem) {
  return (problem.sub_questions || []).every((sub) => Boolean(answers[sub.id]))
}

async function loadHistory() {
  historyLoading.value = true
  try {
    history.value = await mockApi.list()
  } catch {
    /* 忽略 */
  } finally {
    historyLoading.value = false
  }
}

async function startExam() {
  starting.value = true
  try {
    const created = await mockApi.create(examType.value)
    ElMessage.success('组卷完成，计时开始')
    router.push({ name: 'mock-exam-run', params: { id: created.id } })
  } catch (err) {
    ElMessage.error(err.message || '组卷失败')
  } finally {
    starting.value = false
  }
}

function saveDraft() {
  try {
    localStorage.setItem(draftKey.value, JSON.stringify(answers))
  } catch {
    /* 忽略隐私模式写入失败 */
  }
}

function restoreDraft() {
  try {
    const raw = localStorage.getItem(draftKey.value)
    if (!raw) return
    const saved = JSON.parse(raw)
    Object.entries(saved).forEach(([key, value]) => {
      if (value) answers[key] = value
    })
  } catch {
    /* 忽略 */
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(draftKey.value)
  } catch {
    /* 忽略 */
  }
}

async function loadExam() {
  loading.value = true
  try {
    const data = await mockApi.detail(examId.value)
    exam.value = data
    if (data.status === 'submitted') {
      router.replace({ name: 'mock-exam-result', params: { id: examId.value } })
      return
    }
    remaining.value = data.remaining_seconds ?? 120 * 60
    restoreDraft()
    startTimer()
  } catch (err) {
    ElMessage.error(err.message || '考试加载失败')
    router.replace({ name: 'mock-exams' })
  } finally {
    loading.value = false
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(() => {
    remaining.value -= 1
    if (remaining.value <= 0) {
      remaining.value = 0
      stopTimer()
      submitExam(true)
    }
  }, 1000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function goTo(index) {
  if (index < 0 || index >= problems.value.length) return
  currentIndex.value = index
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitExam(auto = false) {
  if (submitting.value || submitted.value) return
  const unanswered = totalSubs.value - answeredSubs.value

  if (!auto) {
    const ok = await confirm({
      title: '交卷',
      message: unanswered
        ? `还有 ${unanswered} 个小题未作答，确定交卷吗？交卷后不可修改。`
        : '所有小题均已作答，确定交卷吗？交卷后不可修改。',
      confirmText: '交卷',
    })
    if (!ok) return
  }

  submitting.value = true
  stopTimer()
  try {
    const payload = {}
    Object.entries(answers).forEach(([key, value]) => {
      if (value) payload[key] = value
    })
    await mockApi.submit(examId.value, payload)
    submitted.value = true
    clearDraft()
    ElMessage.success(auto ? '考试时间到，已自动交卷' : '交卷成功，正在判分')
    router.replace({ name: 'mock-exam-result', params: { id: examId.value } })
  } catch (err) {
    ElMessage.error(err.message || '交卷失败')
    startTimer()
  } finally {
    submitting.value = false
  }
}

watch(answers, saveDraft, { deep: true })

onBeforeRouteLeave(async () => {
  if (!running.value || submitted.value || loading.value || !exam.value) return true
  if (exam.value.status !== 'ongoing') return true
  stopTimer()
  const ok = await confirm({
    title: '离开考试',
    message: '离开后本次作答将保存在本机草稿中，但不会自动交卷。确定离开吗？',
    confirmText: '离开',
    danger: true,
  })
  if (ok) return true
  startTimer()
  return false
})

watch(
  () => route.params.id,
  async (id) => {
    stopTimer()
    if (id) {
      await loadExam()
    } else {
      exam.value = null
      currentIndex.value = 0
      Object.keys(answers).forEach((key) => delete answers[key])
      await loadHistory()
    }
  },
  { immediate: true },
)

onBeforeUnmount(stopTimer)
</script>

<template>
  <div v-if="!running" class="page">
    <div class="page-title">
      模拟考试
      <span class="sub">20 题 · 120 分钟</span>
    </div>

    <section class="intro card">
      <div class="intro-main">
        <h1>CSP 第一轮模拟卷</h1>
        <p>15 道单项选择 + 3 道阅读程序 + 2 道完善程序，满分 100 分。</p>

        <div class="structure">
          <div v-for="item in STRUCTURE" :key="item.label" class="structure-item">
            <p class="st-label">{{ item.label }}</p>
            <p class="st-count">{{ item.count }} 题 · {{ item.score }} 分</p>
            <p class="st-desc">{{ item.desc }}</p>
          </div>
        </div>

        <div class="start-row">
          <el-radio-group v-model="examType">
            <el-radio-button value="J">CSP-J 入门级</el-radio-button>
            <el-radio-button value="S">CSP-S 提高级</el-radio-button>
          </el-radio-group>
          <el-button type="primary" size="large" :loading="starting" @click="startExam">
            开始考试
          </el-button>
        </div>
        <p class="intro-tip">开始后立即计时，中途离开会保留本机草稿。</p>
      </div>

      <aside class="intro-side">
        <h3>历史成绩</h3>
        <div v-loading="historyLoading" class="history">
          <div
            v-for="item in history"
            :key="item.id"
            class="history-item"
            @click="item.status === 'submitted' && router.push({ name: 'mock-exam-result', params: { id: item.id } })"
          >
            <div>
              <p class="hi-type">{{ item.exam_type === 'J' ? 'CSP-J' : 'CSP-S' }} 模拟卷</p>
              <p class="hi-time">{{ formatDate(item.started_at, true) }}</p>
            </div>
            <div class="hi-right">
              <span v-if="item.status === 'submitted'" class="hi-score">{{ item.score }} 分</span>
              <el-tag v-else size="small" type="warning" effect="plain">进行中</el-tag>
            </div>
          </div>
          <p v-if="!history.length && !historyLoading" class="muted empty-history">还没有模拟考试记录</p>
        </div>
      </aside>
    </section>
  </div>

  <div v-else class="page exam-page">
    <div v-if="loading" v-loading="true" class="card skeleton" />

    <template v-else-if="exam">
      <div class="exam-bar card">
        <div class="eb-left">
          <el-tag size="small" type="success" effect="plain">
            {{ exam.exam_type === 'J' ? 'CSP-J' : 'CSP-S' }} 模拟卷
          </el-tag>
          <span class="eb-count">已答 {{ answeredSubs }} / {{ totalSubs }} 小题</span>
        </div>
        <div class="eb-right">
          <span class="timer" :class="timerTone">{{ formatDuration(remaining) }}</span>
          <el-button type="primary" :loading="submitting" @click="submitExam(false)">交卷</el-button>
        </div>
      </div>

      <div class="exam-layout">
        <main class="exam-main">
          <article v-if="currentProblem" class="card question-card">
            <div class="qc-head">
              <span class="qc-index">第 {{ currentIndex + 1 }} 题</span>
              <span class="type-badge" :class="currentProblem.type">
                {{ TYPE_LABELS[currentProblem.type] }}
              </span>
              <span class="spacer" />
              <span class="muted qc-meta">
                {{ (currentProblem.sub_questions || []).length }} 个小题 · 本题
                {{ mockProblemPoints(currentIndex) }} 分
              </span>
            </div>
            <h2 class="qc-title">{{ currentProblem.title }}</h2>

            <div class="qc-content">
              <MarkdownView :content="currentProblem.content_md" />
            </div>

            <div class="qc-subs">
              <SubQuestionBlock
                v-for="(sub, subIndex) in currentProblem.sub_questions"
                :key="sub.id"
                v-model="answers[sub.id]"
                :sub="sub"
                :index="subIndex + 1"
              />
            </div>
          </article>

          <div class="nav-row">
            <el-button :disabled="currentIndex === 0" @click="goTo(currentIndex - 1)">上一题</el-button>
            <el-button :disabled="currentIndex >= problems.length - 1" type="primary" plain @click="goTo(currentIndex + 1)">
              下一题
            </el-button>
            <span class="spacer" />
            <el-button :loading="submitting" @click="submitExam(false)">交卷</el-button>
          </div>
        </main>

        <aside class="exam-side">
          <div class="card sheet">
            <h3 class="sheet-title">答题卡</h3>
            <p class="sheet-hint">绿色为已作答，点击题号可跳转</p>
            <div v-for="section in sections" :key="section.title" class="sheet-section">
              <p class="sheet-section-title">{{ section.title }}</p>
              <div class="sheet-grid">
                <button
                  v-for="item in section.items"
                  :key="item.problem.id"
                  class="sheet-cell"
                  :class="{
                    answered: problemAnswered(item.problem),
                    active: item.index === currentIndex,
                    complete: problemComplete(item.problem),
                  }"
                  @click="goTo(item.index)"
                >
                  {{ item.index + 1 }}
                </button>
              </div>
            </div>
            <el-button type="primary" class="sheet-submit" :loading="submitting" @click="submitExam(false)">
              交卷并查看解析
            </el-button>
          </div>
        </aside>
      </div>
    </template>

    <EmptyState
      v-else
      title="无法加载试卷"
      description="试卷可能已被删除，或者链接有误。"
      action-text="返回模拟考试"
      @action="router.replace({ name: 'mock-exams' })"
    />
  </div>
</template>

<style scoped>
.skeleton {
  min-height: 220px;
}

.intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 26px;
  padding: 28px;
}

.intro-main h1 {
  margin: 0 0 10px;
  font-size: 25px;
}

.intro-main > p {
  margin: 0 0 18px;
  color: #55697a;
  font-size: 14px;
  line-height: 1.9;
}

.structure {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

@media (max-width: 820px) {
  .structure {
    grid-template-columns: 1fr;
  }
}

.structure-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  background: #fcfdfe;
}

.st-label {
  margin: 0 0 4px;
  font-weight: 650;
  font-size: 14px;
}

.st-count {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--brand-dark);
  font-family: var(--mono);
}

.st-desc {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}

.start-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.intro-tip {
  margin: 12px 0 0;
  font-size: 12px;
  color: #8a99a8;
}

.intro-side h3 {
  margin: 0 0 10px;
  font-size: 15px;
}

.history {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 60px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.history-item:hover {
  border-color: #c3ded5;
}

.hi-type {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
}

.hi-time {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: var(--muted);
}

.hi-score {
  font-family: var(--mono);
  font-weight: 700;
  font-size: 15px;
  color: var(--brand-dark);
}

.empty-history {
  font-size: 12.5px;
}

.exam-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 18px;
  position: sticky;
  top: 70px;
  z-index: 20;
  flex-wrap: wrap;
}

.eb-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eb-count {
  font-size: 13px;
  color: var(--muted);
}

.eb-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timer {
  font-family: var(--mono);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--brand-dark);
  background: var(--brand-soft);
  padding: 3px 12px;
  border-radius: 8px;
}

.timer.danger {
  color: #a33b38;
  background: var(--bad-soft);
}

.exam-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 264px;
  gap: 18px;
  margin-top: 16px;
  align-items: start;
}

@media (max-width: 900px) {
  .exam-layout {
    grid-template-columns: 1fr;
  }
}

.question-card {
  padding: 22px 24px;
}

.qc-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qc-index {
  font-family: var(--mono);
  font-size: 12.5px;
  color: var(--brand-dark);
  background: var(--brand-soft);
  padding: 2px 10px;
  border-radius: 999px;
}

.qc-meta {
  font-size: 12.5px;
}

.qc-title {
  margin: 10px 0 14px;
  font-size: 19px;
}

.qc-content {
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}

.qc-subs {
  margin-top: 6px;
}

.nav-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}

.sheet {
  position: sticky;
  top: 138px;
  padding: 16px 18px;
}

.sheet-title {
  margin: 0 0 4px;
  font-size: 15px;
}

.sheet-hint {
  margin: 0 0 12px;
  font-size: 11.5px;
  color: var(--muted);
}

.sheet-section + .sheet-section {
  margin-top: 12px;
}

.sheet-section-title {
  margin: 0 0 7px;
  font-size: 12px;
  color: #7d8c9b;
}

.sheet-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}

.sheet-cell {
  height: 30px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: #fff;
  color: #55697a;
  font-family: var(--mono);
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sheet-cell:hover {
  border-color: var(--brand);
  color: var(--brand-dark);
}

.sheet-cell.answered {
  background: var(--brand-soft);
  border-color: #b9d6cd;
  color: var(--brand-dark);
}

.sheet-cell.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px rgba(31, 111, 92, 0.18);
  font-weight: 700;
}

.sheet-submit {
  width: 100%;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .sheet {
    position: static;
  }

  .exam-bar {
    position: static;
  }
}
</style>
