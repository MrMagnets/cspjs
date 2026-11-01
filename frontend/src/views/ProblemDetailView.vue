<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listApi, problemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import MarkdownView from '@/components/MarkdownView.vue'
import SubQuestionBlock from '@/components/SubQuestionBlock.vue'
import EmptyState from '@/components/EmptyState.vue'
import { SOURCE_LABELS, STATUS_META, TYPE_LABELS, formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { confirm, prompt } = useConfirmDialog()

const loading = ref(true)
const notFound = ref(false)
const problem = ref(null)
const answers = reactive({})
const result = ref(null)
const submitting = ref(false)

const listDialogVisible = ref(false)
const myLists = ref([])
const chosenListId = ref(null)

const problemId = computed(() => Number(route.params.id))

const resultMap = computed(() => {
  const map = {}
  ;(result.value?.items || []).forEach((item) => {
    map[item.sub_question_id] = item
  })
  return map
})

const canEdit = computed(() => {
  if (!auth.isLoggedIn || !problem.value) return false
  if (auth.isAdmin) return true
  return problem.value.contributor_id === auth.user?.id && problem.value.status !== 'approved'
})

const isPendingReview = computed(() => problem.value?.status === 'pending' && auth.isAdmin)

const sourceText = computed(() => {
  const p = problem.value
  if (!p) return ''
  return [SOURCE_LABELS[p.source_tag] || p.source_tag, p.source_year, p.source_exam].filter(Boolean).join(' · ')
})

const answeredCount = computed(() => Object.values(answers).filter((v) => Boolean(v)).length)

const resultTone = computed(() => {
  if (!result.value) return ''
  const { correct_count: c, total_count: t } = result.value
  if (c === t) return 'ok'
  if (c === 0) return 'bad'
  return 'partial'
})

async function load() {
  loading.value = true
  notFound.value = false
  result.value = null
  try {
    problem.value = await problemApi.detail(problemId.value)
    Object.keys(answers).forEach((k) => delete answers[k])
  } catch (err) {
    notFound.value = true
    ElMessage.error(err.message || '题目加载失败')
  } finally {
    loading.value = false
  }
}

async function submitAnswers() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能提交答案')
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!answeredCount.value) {
    ElMessage.warning('请先选择答案')
    return
  }
  submitting.value = true
  try {
    result.value = await problemApi.answer(problemId.value, { ...answers })
    const { correct_count: c, total_count: t } = result.value
    if (c === t) ElMessage.success(`全部答对，${c}/${t}`)
    else ElMessage.warning(`答对 ${c}/${t}，已自动加入错题本`)
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function retry() {
  const ok = await confirm({ title: '重新作答', message: '将清空本次作答结果，重新开始？' })
  if (!ok) return
  result.value = null
  Object.keys(answers).forEach((k) => delete answers[k])
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function removeProblem() {
  const ok = await confirm({
    title: '删除题目',
    message: '删除后不可恢复，确定删除这道题吗？',
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await problemApi.remove(problemId.value)
    ElMessage.success('已删除')
    router.replace({ name: 'my-problems' })
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

async function approve() {
  const ok = await confirm({
    title: '通过审核',
    message: '通过后该题目将进入公共题库，确定通过吗？',
    confirmText: '通过',
  })
  if (!ok) return
  try {
    problem.value = await problemApi.review(problemId.value, { action: 'approve' })
    ElMessage.success('已通过审核')
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function reject() {
  const reason = await prompt({
    title: '驳回题目',
    message: '请填写驳回原因，作者可据此修改后重新提交。',
    placeholder: '例如：题干描述有歧义，选项 B 与 D 重复',
    required: true,
    confirmText: '确认驳回',
    danger: true,
  })
  if (!reason) return
  try {
    problem.value = await problemApi.review(problemId.value, { action: 'reject', reason })
    ElMessage.success('已驳回')
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function openListDialog() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  try {
    myLists.value = await listApi.list({ scope: 'mine' })
    chosenListId.value = myLists.value[0]?.id ?? null
    listDialogVisible.value = true
  } catch (err) {
    ElMessage.error(err.message || '题单加载失败')
  }
}

async function addToList() {
  if (!chosenListId.value) return
  try {
    await listApi.addItem(chosenListId.value, problemId.value)
    ElMessage.success('已加入题单')
    listDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '加入失败')
  }
}

watch(() => route.params.id, load)

onMounted(load)
</script>

<template>
  <div class="page">
    <div v-if="loading" v-loading="true" class="skeleton-card card" />

    <template v-else-if="notFound">
      <div class="card">
        <EmptyState
          title="无法查看该题目"
          description="题目可能尚未通过审核、已被删除，或者链接有误。"
          action-text="返回题库"
          @action="router.push({ name: 'problems' })"
        />
      </div>
    </template>

    <template v-else-if="problem">
      <div class="detail-head card">
        <div class="head-top">
          <span class="type-badge" :class="problem.type">{{ TYPE_LABELS[problem.type] }}</span>
          <el-tag v-if="problem.status !== 'approved'" size="small" :type="STATUS_META[problem.status]?.type">
            {{ STATUS_META[problem.status]?.label }}
          </el-tag>
          <span class="spacer" />
          <div class="head-actions">
            <el-button size="small" @click="openListDialog">加入题单</el-button>
            <el-button v-if="canEdit" size="small" @click="router.push({ name: 'problem-edit', params: { id: problem.id } })">
              编辑
            </el-button>
            <el-button v-if="canEdit" size="small" type="danger" plain @click="removeProblem">删除</el-button>
          </div>
        </div>

        <h1 class="title">{{ problem.title }}</h1>

        <div class="meta">
          <span>{{ sourceText }}</span>
          <span class="dot-sep">·</span>
          <span>{{ problem.sub_question_count }} 个小题</span>
          <span class="dot-sep">·</span>
          <span>贡献者 {{ problem.contributor_name }}</span>
          <span class="dot-sep">·</span>
          <span>发布于 {{ formatDate(problem.created_at) }}</span>
          <span v-if="problem.reviewed_at" class="dot-sep">·</span>
          <span v-if="problem.reviewed_at">审核于 {{ formatDate(problem.reviewed_at) }}</span>
        </div>

        <div v-if="problem.tags?.length" class="tags">
          <span v-for="tag in problem.tags" :key="tag.id" class="tag">{{ tag.name }}</span>
        </div>

        <div v-if="problem.status === 'rejected' && problem.reject_reason" class="reject-box">
          <b>驳回原因：</b>{{ problem.reject_reason }}
        </div>
      </div>

      <div v-if="isPendingReview" class="review-bar card">
        <div>
          <p class="rb-title">这道题正在等待审核</p>
          <p class="rb-desc">请核对题干、选项、正确答案与解析是否自洽。</p>
        </div>
        <div class="row">
          <el-button type="danger" plain @click="reject">驳回</el-button>
          <el-button type="primary" @click="approve">通过</el-button>
        </div>
      </div>

      <div class="card content-card">
        <MarkdownView :content="problem.content_md" />

        <div class="sub-list">
          <SubQuestionBlock
            v-for="(sub, index) in problem.sub_questions"
            :key="sub.id"
            v-model="answers[sub.id]"
            :sub="sub"
            :index="index + 1"
            :disabled="Boolean(result)"
            :result="resultMap[sub.id] || null"
            :show-answer="Boolean(result)"
          />
        </div>

        <div v-if="result" class="result-banner" :class="resultTone">
          本次作答：答对 {{ result.correct_count }} / {{ result.total_count }} 题
          <span class="rate">正确率 {{ Math.round(result.score_rate * 100) }}%</span>
        </div>

        <div class="answer-actions">
          <template v-if="!result">
            <span class="muted answer-hint">
              {{ auth.isLoggedIn ? `已作答 ${answeredCount} / ${problem.sub_questions.length}` : '登录后可提交答案并查看解析' }}
            </span>
            <el-button type="primary" :loading="submitting" @click="submitAnswers">提交答案</el-button>
          </template>
          <template v-else>
            <span class="muted answer-hint">做错的题目已自动进入错题本</span>
            <el-button @click="retry">再做一次</el-button>
            <el-button type="primary" plain @click="router.push({ name: 'wrong-book' })">去错题本</el-button>
          </template>
        </div>
      </div>

      <div v-if="problem.answer_md" class="card">
        <h2 class="section-title">整体解析</h2>
        <MarkdownView :content="problem.answer_md" />
      </div>

      <div v-else-if="!result" class="card muted small-tip">
        提交答案后，每道小题会展示逐题解析；整卷解析由出题人补充，可在题干下方查看。
      </div>
    </template>

    <el-dialog v-model="listDialogVisible" title="加入题单" width="420px" align-center>
      <template v-if="myLists.length">
        <el-select v-model="chosenListId" placeholder="选择题单" style="width: 100%">
          <el-option v-for="list in myLists" :key="list.id" :label="list.title" :value="list.id" />
        </el-select>
        <p class="muted dialog-hint">仅可收录已通过审核的题目。</p>
      </template>
      <EmptyState
        v-else
        title="还没有题单"
        description="先创建一个题单，再把题目收录进去"
        action-text="去创建题单"
        @action="router.push({ name: 'lists' })"
      />
      <template #footer>
        <el-button @click="listDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!chosenListId" @click="addToList">加入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.skeleton-card {
  min-height: 220px;
}

.detail-head {
  padding: 22px 24px;
}

.head-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.title {
  margin: 12px 0 10px;
  font-size: 24px;
  line-height: 1.45;
  letter-spacing: 0.3px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  color: var(--muted);
}

.dot-sep {
  color: #c8d2dd;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}

.tag {
  font-size: 12.5px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  border: 1px solid #cfe4dd;
}

.reject-box {
  margin-top: 14px;
  padding: 10px 14px;
  background: var(--bad-soft);
  border: 1px solid #f4cfcd;
  border-radius: 9px;
  color: #a33b38;
  font-size: 13.5px;
}

.review-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-left: 4px solid var(--warn);
  flex-wrap: wrap;
}

.rb-title {
  margin: 0 0 3px;
  font-weight: 700;
  font-size: 15px;
}

.rb-desc {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.content-card {
  padding: 26px 26px 22px;
}

.sub-list {
  margin-top: 18px;
  border-top: 1px solid var(--border);
}

.answer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed var(--border);
}

.answer-hint {
  margin-right: auto;
  font-size: 13px;
}

.rate {
  margin-left: 10px;
  font-weight: 400;
  opacity: 0.85;
}

.section-title {
  margin: 0 0 12px;
  font-size: 17px;
}

.small-tip {
  font-size: 13px;
}

.dialog-hint {
  margin: 12px 0 0;
  font-size: 12.5px;
}
</style>
