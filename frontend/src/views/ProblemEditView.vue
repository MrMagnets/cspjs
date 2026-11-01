<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { problemApi, tagApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import { SOURCE_LABELS, TYPE_LABELS } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { confirm, prompt } = useConfirmDialog()

const LETTERS = 'ABCDEFGH'
const MAX_OPTIONS = 6

const loading = ref(false)
const saving = ref(false)
const tags = ref([])
const subEditors = ref([])

const isEdit = computed(() => Boolean(route.params.id))
const pageTitle = computed(() => (isEdit.value ? '编辑题目' : '投稿题目'))

const form = reactive({
  title: '',
  type: 'single',
  source_tag: 'original',
  source_year: null,
  source_exam: 'CSP-J',
  content_md: '',
  answer_md: '',
  tag_ids: [],
})

const tagGroups = computed(() => {
  const groups = {}
  tags.value.forEach((tag) => {
    const key = tag.category || '其他'
    if (!groups[key]) groups[key] = []
    groups[key].push(tag)
  })
  return groups
})

const knowledgeTags = computed(() => tags.value.filter((t) => t.category === '知识点'))

function newSub(withContent = true) {
  return {
    content_md: '',
    options: ['A', 'B', 'C', 'D'].map((key) => ({ key, text: '' })),
    correct_answer: 'A',
    analysis_md: withContent ? '' : '',
  }
}

function ensureSubCount() {
  if (form.type === 'single') {
    if (subEditors.value.length !== 1) subEditors.value = [subEditors.value[0] || newSub()]
    return
  }
  if (subEditors.value.length < 2) {
    while (subEditors.value.length < 2) subEditors.value.push(newSub())
  }
}

function addSub() {
  if (subEditors.value.length >= 10) {
    ElMessage.warning('单题最多 10 个小题')
    return
  }
  subEditors.value.push(newSub())
}

async function removeSub(index) {
  if (subEditors.value.length <= 1) {
    ElMessage.warning('至少保留一个小题')
    return
  }
  const ok = await confirm({
    title: '删除小题',
    message: `确定删除第 ${index + 1} 个小题吗？`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  subEditors.value.splice(index, 1)
}

function addOption(sub) {
  if (sub.options.length >= MAX_OPTIONS) {
    ElMessage.warning(`每题最多 ${MAX_OPTIONS} 个选项`)
    return
  }
  sub.options.push({ key: LETTERS[sub.options.length], text: '' })
}

function removeOption(sub, index) {
  if (sub.options.length <= 2) {
    ElMessage.warning('至少保留 2 个选项')
    return
  }
  sub.options.splice(index, 1)
  sub.options.forEach((opt, i) => {
    opt.key = LETTERS[i]
  })
  if (!sub.options.some((opt) => opt.key === sub.correct_answer)) {
    sub.correct_answer = sub.options[0].key
  }
}

async function loadTags() {
  try {
    tags.value = await tagApi.list()
  } catch {
    /* 忽略 */
  }
}

async function loadProblem() {
  loading.value = true
  try {
    const data = await problemApi.detail(route.params.id)
    form.title = data.title
    form.type = data.type
    form.source_tag = data.source_tag
    form.source_year = data.source_year
    form.source_exam = data.source_exam
    form.content_md = data.content_md
    form.answer_md = data.answer_md
    form.tag_ids = (data.tags || []).map((t) => t.id)
    subEditors.value = data.sub_questions.map((sq) => ({
      content_md: sq.content_md,
      options: (sq.options || []).map((o) => ({ key: o.key, text: o.text })),
      correct_answer: sq.correct_answer,
      analysis_md: sq.analysis_md,
    }))
    if (!subEditors.value.length) subEditors.value = [newSub()]
  } catch (err) {
    ElMessage.error(err.message || '题目加载失败')
    router.back()
  } finally {
    loading.value = false
  }
}

async function createTag() {
  const name = await prompt({
    title: '新建知识点标签',
    message: '输入标签名，例如「前缀和」「并查集」。',
    placeholder: '标签名',
    required: true,
    maxlength: 64,
    confirmText: '创建',
  })
  if (!name) return
  try {
    const tag = await tagApi.create({ name, category: '知识点' })
    if (!tags.value.some((t) => t.id === tag.id)) tags.value.push(tag)
    if (!form.tag_ids.includes(tag.id)) form.tag_ids.push(tag.id)
    ElMessage.success('标签已创建')
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  }
}

function validate() {
  if (form.title.trim().length < 2) return '标题至少 2 个字符'
  if (!form.content_md.trim()) return '题干不能为空'
  if (form.type === 'single' && subEditors.value.length !== 1) return '单选题必须且只能包含 1 个小题'
  if (form.type !== 'single' && subEditors.value.length < 2) return '阅读程序 / 完善程序题至少需要 2 个小题'
  for (let i = 0; i < subEditors.value.length; i += 1) {
    const sub = subEditors.value[i]
    const filled = sub.options.filter((opt) => opt.text.trim())
    if (filled.length < 2) return `第 ${i + 1} 个小题至少需要 2 个有内容的选项`
    if (!filled.some((opt) => opt.key === sub.correct_answer)) {
      return `第 ${i + 1} 个小题的正确答案不在有效选项中`
    }
    if (form.type !== 'single' && !sub.content_md.trim()) {
      return `第 ${i + 1} 个小题的题干不能为空`
    }
  }
  return ''
}

async function save() {
  const error = validate()
  if (error) {
    ElMessage.error(error)
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      type: form.type,
      source_tag: form.source_tag,
      source_year: form.source_year || null,
      source_exam: form.source_exam || null,
      content_md: form.content_md,
      answer_md: form.answer_md,
      tag_ids: form.tag_ids,
      sub_questions: subEditors.value.map((sub) => ({
        content_md: sub.content_md,
        options: sub.options.filter((opt) => opt.text.trim()).map((opt) => ({ key: opt.key, text: opt.text })),
        correct_answer: sub.correct_answer,
        analysis_md: sub.analysis_md,
      })),
    }
    const saved = isEdit.value
      ? await problemApi.update(route.params.id, payload)
      : await problemApi.create(payload)
    ElMessage.success(
      saved.status === 'approved' ? '保存成功，题目已进入公共题库' : '保存成功，等待管理员审核',
    )
    router.push({ name: 'problem-detail', params: { id: saved.id } })
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function cancel() {
  const ok = await confirm({ title: '放弃编辑', message: '未保存的内容将会丢失，确定离开吗？', confirmText: '离开' })
  if (ok) router.back()
}

watch(
  () => form.type,
  () => ensureSubCount(),
)

onMounted(async () => {
  await loadTags()
  if (isEdit.value) await loadProblem()
  else subEditors.value = [newSub()]
})
</script>

<template>
  <div class="page">
    <div class="page-title">
      {{ pageTitle }}
      <span class="sub">
        {{ auth.isAdmin ? '管理员投稿将直接通过审核' : '提交后进入待审核队列，仅你与管理员可见' }}
      </span>
    </div>

    <div v-loading="loading" class="edit-layout">
      <div class="edit-main">
        <section class="card">
          <h2 class="block-title">基础信息</h2>
          <el-form label-position="top">
            <el-form-item label="题目标题" required>
              <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="例如：阅读程序：循环与数组" />
            </el-form-item>

            <div class="form-grid">
              <el-form-item label="题型" required>
                <el-radio-group v-model="form.type">
                  <el-radio-button v-for="(label, value) in TYPE_LABELS" :key="value" :value="value">
                    {{ label }}
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="来源" required>
                <el-select v-model="form.source_tag" style="width: 100%">
                  <el-option v-for="(label, value) in SOURCE_LABELS" :key="value" :label="label" :value="value" />
                </el-select>
              </el-form-item>

              <el-form-item label="年份">
                <el-input-number
                  v-model="form.source_year"
                  :min="2000"
                  :max="2100"
                  controls-position="right"
                  style="width: 100%"
                  placeholder="如 2024"
                />
              </el-form-item>

              <el-form-item label="试卷">
                <el-select v-model="form.source_exam" clearable placeholder="不指定" style="width: 100%">
                  <el-option label="CSP-J" value="CSP-J" />
                  <el-option label="CSP-S" value="CSP-S" />
                </el-select>
              </el-form-item>
            </div>

            <el-form-item label="知识点标签">
              <div class="tag-row">
                <el-select
                  v-model="form.tag_ids"
                  multiple
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择知识点 / 来源标签"
                  style="flex: 1"
                >
                  <el-option-group v-for="(group, category) in tagGroups" :key="category" :label="category">
                    <el-option v-for="tag in group" :key="tag.id" :label="tag.name" :value="tag.id" />
                  </el-option-group>
                </el-select>
                <el-button @click="createTag">新建知识点</el-button>
              </div>
            </el-form-item>
          </el-form>
        </section>

        <section class="card">
          <h2 class="block-title">题干</h2>
          <MarkdownEditor v-model="form.content_md" :rows="12" min-height="220px" show-tip />
          <p class="hint">
            阅读程序 / 完善程序题请在题干中给出完整代码；单选题题干写清设问即可，小题中再列选项。
          </p>
        </section>

        <section class="card">
          <div class="block-head">
            <h2 class="block-title" style="margin: 0">小题</h2>
            <el-button v-if="form.type !== 'single'" size="small" plain type="primary" @click="addSub">
              添加小题
            </el-button>
          </div>
          <p class="hint">
            {{ form.type === 'single' ? '单选题固定一个小题。' : '阅读程序 / 完善程序题至少两个小题，按顺序编号 (1)(2)(3)。' }}
          </p>

          <div v-for="(sub, index) in subEditors" :key="index" class="sub-editor">
            <div class="sub-editor-head">
              <span class="sub-badge">{{ index + 1 }}</span>
              <span class="sub-editor-title">第 {{ index + 1 }} 小题</span>
              <span class="spacer" />
              <el-button
                v-if="form.type !== 'single'"
                link
                type="danger"
                size="small"
                @click="removeSub(index)"
              >
                删除小题
              </el-button>
            </div>

            <el-form label-position="top">
              <el-form-item :label="form.type === 'single' ? '小题题干（可留空，默认「请选择正确答案」）' : '小题题干'">
                <MarkdownEditor v-model="sub.content_md" :rows="3" placeholder="例如：(1) 该程序的时间复杂度是（ ）" />
              </el-form-item>

              <el-form-item label="选项" required>
                <div class="option-editor-list">
                  <div v-for="(option, optIndex) in sub.options" :key="option.key" class="option-editor">
                    <span class="option-key">{{ option.key }}</span>
                    <el-input v-model="option.text" placeholder="选项内容，支持 Markdown 与公式" />
                    <el-button
                      link
                      type="danger"
                      size="small"
                      :disabled="sub.options.length <= 2"
                      @click="removeOption(sub, optIndex)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
                <el-button size="small" plain style="margin-top: 8px" @click="addOption(sub)">添加选项</el-button>
              </el-form-item>

              <el-form-item label="正确答案" required>
                <el-radio-group v-model="sub.correct_answer">
                  <el-radio-button v-for="option in sub.options" :key="option.key" :value="option.key">
                    {{ option.key }}
                  </el-radio-button>
                </el-radio-group>
                <span class="hint inline">第一轮初赛均为单项选择。</span>
              </el-form-item>

              <el-form-item label="小题解析">
                <MarkdownEditor v-model="sub.analysis_md" :rows="3" placeholder="说明解题思路与易错点，提交后可展示给考生" />
              </el-form-item>
            </el-form>
          </div>
        </section>

        <section class="card">
          <h2 class="block-title">整体解析（可选）</h2>
          <MarkdownEditor v-model="form.answer_md" :rows="5" show-tip placeholder="整题的整体思路、考点总结等" />
        </section>

        <div class="save-bar">
          <el-button @click="cancel">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">
            {{ isEdit ? '保存修改' : '提交审核' }}
          </el-button>
        </div>
      </div>

      <aside class="edit-side">
        <div class="card sticky">
          <h3 class="side-title">发布规则</h3>
          <ul class="rules">
            <li>普通用户提交后状态为「待审核」，仅本人与管理员可见。</li>
            <li>审核通过后进入公共题库；被驳回可按原因修改后重新提交。</li>
            <li>已通过的题目普通用户不可直接修改，需联系管理员。</li>
            <li>阅读 / 完善程序题的小题编号即考试中的 (1)(2)(3)。</li>
          </ul>

          <h3 class="side-title" style="margin-top: 18px">实时预览</h3>
          <div class="preview">
            <p class="preview-type">
              {{ TYPE_LABELS[form.type] }} · {{ SOURCE_LABELS[form.source_tag] }}
            </p>
            <p class="preview-title">{{ form.title || '未命名题目' }}</p>
            <MarkdownView v-if="form.content_md" :content="form.content_md" />
            <p v-else class="muted preview-empty">题干预览将显示在这里</p>

            <div v-if="subEditors.length" class="preview-subs">
              <p v-for="(sub, i) in subEditors" :key="i" class="preview-sub">
                <span class="sub-badge neutral">{{ i + 1 }}</span>
                <span>{{ sub.content_md ? '已填写小题题干' : `小题 ${i + 1}` }}</span>
                <span class="muted">答案 {{ sub.correct_answer }}</span>
              </p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.edit-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}

.edit-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.block-title {
  margin: 0 0 14px;
  font-size: 16.5px;
  font-weight: 700;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.hint {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.8;
}

.hint.inline {
  margin-left: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
}

.tag-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.sub-editor {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px 4px;
  margin-top: 14px;
  background: #fcfdfe;
}

.sub-editor-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.sub-editor-title {
  font-weight: 650;
  font-size: 14.5px;
}

.option-editor-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.option-editor {
  display: flex;
  align-items: center;
  gap: 10px;
}

.option-key {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: #f7f9fb;
  color: var(--muted);
  font-family: var(--mono);
  font-weight: 700;
  font-size: 12.5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.save-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 6px 2px 30px;
}

.sticky {
  position: sticky;
  top: 82px;
}

.side-title {
  margin: 0 0 10px;
  font-size: 14.5px;
  font-weight: 700;
}

.rules {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.9;
}

.preview {
  border-top: 1px dashed var(--border);
  padding-top: 12px;
}

.preview-type {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--brand-dark);
  background: var(--brand-soft);
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
}

.preview-title {
  margin: 8px 0;
  font-size: 14.5px;
  font-weight: 650;
  line-height: 1.5;
}

.preview-empty {
  font-size: 12.5px;
}

.preview-subs {
  margin-top: 12px;
  border-top: 1px dashed var(--border);
  padding-top: 10px;
}

.preview-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
  font-size: 12.5px;
}

.preview-sub :deep(.sub-badge) {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  font-size: 11px;
}

.preview-sub .muted {
  margin-left: auto;
}

@media (max-width: 1000px) {
  .edit-layout {
    grid-template-columns: 1fr;
  }

  .sticky {
    position: static;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
