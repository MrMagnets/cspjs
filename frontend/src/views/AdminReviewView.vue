<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { problemApi } from '@/api'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import MarkdownView from '@/components/MarkdownView.vue'
import EmptyState from '@/components/EmptyState.vue'
import { SOURCE_LABELS, TYPE_LABELS, formatDate } from '@/utils/format'

const router = useRouter()
const { confirm, prompt } = useConfirmDialog()

const loading = ref(true)
const pending = ref([])
const dialogVisible = ref(false)
const current = ref(null)
const detailLoading = ref(false)
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await problemApi.pending({ page_size: 50 })
    pending.value = data.items
  } catch (err) {
    ElMessage.error(err.message || '加载待审列表失败')
  } finally {
    loading.value = false
  }
}

async function open(problem) {
  dialogVisible.value = true
  detailLoading.value = true
  current.value = null
  try {
    current.value = await problemApi.detail(problem.id)
  } catch (err) {
    ElMessage.error(err.message || '题目详情加载失败')
    dialogVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function approve() {
  if (!current.value) return
  const ok = await confirm({
    title: '通过审核',
    message: `确定通过《${current.value.title}》吗？通过后将进入公共题库。`,
    confirmText: '通过',
  })
  if (!ok) return
  acting.value = true
  try {
    await problemApi.review(current.value.id, { action: 'approve' })
    ElMessage.success('已通过审核')
    dialogVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    acting.value = false
  }
}

async function reject() {
  if (!current.value) return
  const reason = await prompt({
    title: '驳回题目',
    message: '请填写驳回原因，作者可据此修改后重新提交。',
    placeholder: '例如：第 (2) 小题答案与解析矛盾',
    required: true,
    confirmText: '确认驳回',
    danger: true,
  })
  if (!reason) return
  acting.value = true
  try {
    await problemApi.review(current.value.id, { action: 'reject', reason })
    ElMessage.success('已驳回')
    dialogVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-title">
      题目审核
      <span class="sub">待审 {{ pending.length }} 道</span>
      <span class="spacer" />
      <el-button size="small" @click="load">刷新</el-button>
    </div>

    <div v-loading="loading" class="review-list">
      <article v-for="problem in pending" :key="problem.id" class="review-item card" @click="open(problem)">
        <div class="ri-head">
          <span class="type-badge" :class="problem.type">{{ TYPE_LABELS[problem.type] }}</span>
          <span class="spacer" />
          <span class="ri-time">{{ formatDate(problem.created_at, true) }}</span>
        </div>
        <h3 class="ri-title">{{ problem.title }}</h3>
        <div class="ri-meta">
          <span>{{ SOURCE_LABELS[problem.source_tag] }}</span>
          <span v-if="problem.source_year"> · {{ problem.source_year }}</span>
          <span v-if="problem.source_exam"> · {{ problem.source_exam }}</span>
          <span> · {{ problem.sub_question_count }} 个小题</span>
          <span> · 投稿人 {{ problem.contributor_name }}</span>
        </div>
        <div v-if="problem.tags?.length" class="ri-tags">
          <span v-for="tag in problem.tags" :key="tag.id" class="ri-tag">{{ tag.name }}</span>
        </div>
        <div class="ri-actions">
          <el-button size="small" type="primary" plain @click.stop="open(problem)">查看并审核</el-button>
        </div>
      </article>
    </div>

    <EmptyState
      v-if="!loading && !pending.length"
      title="没有待审核的题目"
      description="所有投稿都已处理完毕，休息一下吧。"
      action-text="去题库看看"
      @action="router.push({ name: 'problems' })"
    />

    <el-dialog v-model="dialogVisible" width="820px" top="6vh" align-center destroy-on-close>
      <template #header>
        <div class="dialog-head">
          <span>审核题目</span>
          <el-tag v-if="current" size="small" type="warning" effect="light">待审核</el-tag>
        </div>
      </template>

      <div v-loading="detailLoading" class="dialog-body">
        <template v-if="current">
          <div class="rw-meta">
            <span class="type-badge" :class="current.type">{{ TYPE_LABELS[current.type] }}</span>
            <span>{{ SOURCE_LABELS[current.source_tag] }}</span>
            <span v-if="current.source_year"> · {{ current.source_year }}</span>
            <span v-if="current.source_exam"> · {{ current.source_exam }}</span>
            <span> · 投稿人 {{ current.contributor_name }}</span>
            <span> · {{ formatDate(current.created_at, true) }}</span>
          </div>
          <h2 class="rw-title">{{ current.title }}</h2>

          <div v-if="current.tags?.length" class="ri-tags">
            <span v-for="tag in current.tags" :key="tag.id" class="ri-tag">{{ tag.name }}</span>
          </div>

          <div class="rw-content">
            <MarkdownView :content="current.content_md" />
          </div>

          <div class="rw-subs">
            <div v-for="(sub, index) in current.sub_questions" :key="sub.id" class="rw-sub">
              <div class="rw-sub-head">
                <span class="sub-badge">{{ index + 1 }}</span>
                <div class="rw-sub-content">
                  <MarkdownView v-if="sub.content_md" :content="sub.content_md" />
                  <span v-else class="muted">（无小题题干）</span>
                </div>
                <span class="correct-badge">答案 {{ sub.correct_answer }}</span>
              </div>
              <div class="rw-options">
                <div
                  v-for="option in sub.options"
                  :key="option.key"
                  class="rw-option"
                  :class="{ correct: String(sub.correct_answer).includes(option.key) }"
                >
                  <span class="option-key">{{ option.key }}</span>
                  <MarkdownView :content="option.text" />
                </div>
              </div>
              <div v-if="sub.analysis_md" class="rw-analysis">
                <b>解析：</b>
                <MarkdownView :content="sub.analysis_md" />
              </div>
            </div>
          </div>

          <div v-if="current.answer_md" class="rw-answer">
            <h3 class="rw-section">整体解析</h3>
            <MarkdownView :content="current.answer_md" />
          </div>
        </template>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
          <el-button type="danger" plain :disabled="!current || acting" @click="reject">驳回</el-button>
          <el-button type="primary" :loading="acting" :disabled="!current" @click="approve">通过</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.review-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100px;
}

.review-item {
  cursor: pointer;
  transition: all 0.18s ease;
}

.review-item:hover {
  border-color: #c3ded5;
  box-shadow: var(--shadow-hover);
}

.ri-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ri-time {
  font-size: 12px;
  color: var(--muted);
}

.ri-title {
  margin: 8px 0 6px;
  font-size: 16.5px;
}

.ri-meta {
  font-size: 12.5px;
  color: var(--muted);
}

.ri-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.ri-tag {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #f2f5f8;
  color: #55697a;
}

.ri-actions {
  margin-top: 12px;
}

.dialog-head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 16px;
}

.dialog-body {
  max-height: 68vh;
  overflow-y: auto;
  padding-right: 6px;
  min-height: 120px;
}

.rw-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 12.5px;
  color: var(--muted);
}

.rw-title {
  margin: 10px 0;
  font-size: 20px;
  line-height: 1.5;
}

.rw-content {
  margin-top: 14px;
  padding: 16px;
  background: #fcfdfe;
  border: 1px solid var(--border);
  border-radius: 10px;
}

.rw-subs {
  margin-top: 16px;
}

.rw-sub {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}

.rw-sub + .rw-sub {
  margin-top: 12px;
}

.rw-sub-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.rw-sub-content {
  flex: 1;
  min-width: 0;
}

.correct-badge {
  flex: 0 0 auto;
  font-family: var(--mono);
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--ok-soft);
  color: #1d7a52;
  border: 1px solid #c6e8d8;
}

.rw-options {
  margin: 10px 0 0 36px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rw-option {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
}

.rw-option.correct {
  border-color: var(--ok);
  background: var(--ok-soft);
}

.rw-option :deep(.markdown-body p) {
  margin: 0;
}

.rw-analysis {
  margin: 10px 0 0 36px;
  font-size: 13.5px;
  color: #41525f;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
}

.rw-analysis b {
  color: var(--brand-dark);
}

.rw-answer {
  margin-top: 18px;
}

.rw-section {
  margin: 0 0 8px;
  font-size: 15px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
