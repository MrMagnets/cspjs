<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listApi, problemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import EmptyState from '@/components/EmptyState.vue'
import { SOURCE_LABELS, TYPE_SHORT, formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { confirm } = useConfirmDialog()

const loading = ref(true)
const list = ref(null)
const errorText = ref('')

const editVisible = ref(false)
const editForm = reactive({ title: '', description: '', is_public: true })
const saving = ref(false)

const addVisible = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)
const addingId = ref(null)

const owner = computed(() => auth.isAdmin || (list.value && list.value.creator_id === auth.user?.id))
const listId = computed(() => Number(route.params.id))

async function load() {
  loading.value = true
  errorText.value = ''
  try {
    list.value = await listApi.detail(listId.value)
  } catch (err) {
    errorText.value = err.message || '题单加载失败'
  } finally {
    loading.value = false
  }
}

function openEdit() {
  editForm.title = list.value.title
  editForm.description = list.value.description
  editForm.is_public = list.value.is_public
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  saving.value = true
  try {
    list.value = await listApi.update(listId.value, {
      title: editForm.title.trim(),
      description: editForm.description,
      is_public: editForm.is_public,
    })
    ElMessage.success('已保存')
    editVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function searchProblems() {
  searching.value = true
  try {
    const data = await problemApi.list({
      keyword: searchKeyword.value.trim() || undefined,
      status: 'approved',
      page_size: 20,
    })
    searchResults.value = data.items
  } catch (err) {
    ElMessage.error(err.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

async function addProblem(problem) {
  addingId.value = problem.id
  try {
    list.value = await listApi.addItem(listId.value, problem.id)
    ElMessage.success('已加入题单')
    addVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '加入失败')
  } finally {
    addingId.value = null
  }
}

async function removeProblem(problem) {
  const ok = await confirm({
    title: '移出题单',
    message: `确定把《${problem.title}》移出题单吗？`,
    confirmText: '移出',
    danger: true,
  })
  if (!ok) return
  try {
    list.value = await listApi.removeItem(listId.value, problem.id)
    ElMessage.success('已移出')
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function move(index, delta) {
  const items = [...list.value.problems]
  const target = index + delta
  if (target < 0 || target >= items.length) return
  const [moved] = items.splice(index, 1)
  items.splice(target, 0, moved)
  try {
    list.value = await listApi.reorder(
      listId.value,
      items.map((p) => p.id),
    )
  } catch (err) {
    ElMessage.error(err.message || '排序失败')
  }
}

async function removeList() {
  const ok = await confirm({
    title: '删除题单',
    message: `确定删除题单《${list.value.title}》吗？题单内的题目不会被删除。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await listApi.remove(listId.value)
    ElMessage.success('题单已删除')
    router.replace({ name: 'lists' })
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

function openAdd() {
  addVisible.value = true
  searchKeyword.value = ''
  searchProblems()
}

function startPractice() {
  const first = list.value?.problems?.[0]
  if (!first) {
    ElMessage.warning('题单里还没有题目')
    return
  }
  router.push({ name: 'problem-detail', params: { id: first.id } })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div v-if="loading" v-loading="true" class="card skeleton" />

    <div v-else-if="errorText" class="card">
      <EmptyState
        :title="'无法查看该题单'"
        :description="errorText"
        action-text="返回题单列表"
        @action="router.push({ name: 'lists' })"
      />
    </div>

    <template v-else-if="list">
      <div class="card head-card">
        <div class="hc-top">
          <el-tag size="small" :type="list.is_public ? 'success' : 'info'" effect="plain">
            {{ list.is_public ? '公开题单' : '私有题单' }}
          </el-tag>
          <span class="spacer" />
          <div class="row">
            <el-button v-if="owner" size="small" @click="openEdit">编辑信息</el-button>
            <el-button v-if="owner" size="small" type="primary" plain @click="openAdd">添加题目</el-button>
            <el-button v-if="owner" size="small" type="danger" plain @click="removeList">删除题单</el-button>
          </div>
        </div>

        <h1 class="hc-title">{{ list.title }}</h1>
        <p class="hc-desc">{{ list.description || '暂无描述' }}</p>
        <div class="hc-meta">
          <span>{{ list.problem_count }} 道题</span>
          <span class="dot-sep">·</span>
          <span>创建者 {{ list.creator_name }}</span>
          <span class="dot-sep">·</span>
          <span>{{ formatDate(list.created_at) }}</span>
        </div>

        <div class="hc-actions">
          <el-button type="primary" :disabled="!list.problems.length" @click="startPractice">
            开始刷题
          </el-button>
        </div>
      </div>

      <div class="card">
        <h2 class="section-title">题目列表</h2>

        <div v-if="list.problems.length" class="items">
          <div v-for="(problem, index) in list.problems" :key="problem.id" class="item">
            <span class="item-index">{{ index + 1 }}</span>
            <div class="item-main" @click="router.push({ name: 'problem-detail', params: { id: problem.id } })">
              <p class="item-title">{{ problem.title }}</p>
              <div class="item-meta">
                <span class="type-badge" :class="problem.type">{{ TYPE_SHORT[problem.type] }}</span>
                <span>{{ SOURCE_LABELS[problem.source_tag] }}</span>
                <span v-if="problem.source_year"> · {{ problem.source_year }}</span>
                <span v-if="problem.source_exam"> · {{ problem.source_exam }}</span>
                <span> · {{ problem.sub_question_count }} 个小题</span>
              </div>
            </div>
            <div v-if="owner" class="item-actions">
              <el-button size="small" text :disabled="index === 0" @click="move(index, -1)">↑</el-button>
              <el-button
                size="small"
                text
                :disabled="index === list.problems.length - 1"
                @click="move(index, 1)"
              >
                ↓
              </el-button>
              <el-button size="small" link type="danger" @click="removeProblem(problem)">移出</el-button>
            </div>
          </div>
        </div>

        <EmptyState
          v-else
          title="题单里还没有题目"
          description="从题库中挑选已通过审核的题目加入这个题单。"
          :action-text="owner ? '添加题目' : ''"
          @action="openAdd"
        />
      </div>

      <el-dialog v-model="editVisible" title="编辑题单信息" width="480px" align-center>
        <el-form label-position="top">
          <el-form-item label="标题" required>
            <el-input v-model="editForm.title" maxlength="200" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="可见性">
            <el-switch v-model="editForm.is_public" active-text="公开" inactive-text="私有" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="addVisible" title="添加题目" width="640px" align-center>
        <div class="search-row">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索题目标题或题干"
            clearable
            @keyup.enter="searchProblems"
          />
          <el-button type="primary" :loading="searching" @click="searchProblems">搜索</el-button>
        </div>
        <div v-loading="searching" class="search-results">
          <div v-for="problem in searchResults" :key="problem.id" class="search-item">
            <div class="si-main">
              <p class="si-title">{{ problem.title }}</p>
              <p class="si-meta">
                {{ TYPE_SHORT[problem.type] }} · {{ SOURCE_LABELS[problem.source_tag] }} ·
                {{ problem.sub_question_count }} 个小题
              </p>
            </div>
            <el-button
              size="small"
              type="primary"
              plain
              :loading="addingId === problem.id"
              @click="addProblem(problem)"
            >
              加入
            </el-button>
          </div>
          <p v-if="!searching && !searchResults.length" class="muted empty-tip">没有匹配的题目</p>
        </div>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.skeleton {
  min-height: 200px;
}

.head-card {
  padding: 24px;
}

.hc-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.hc-title {
  margin: 12px 0 8px;
  font-size: 24px;
  line-height: 1.4;
}

.hc-desc {
  margin: 0 0 10px;
  color: #55697a;
  font-size: 14px;
  line-height: 1.8;
}

.hc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12.5px;
  color: var(--muted);
}

.dot-sep {
  color: #c8d2dd;
}

.hc-actions {
  margin-top: 16px;
}

.section-title {
  margin: 0 0 14px;
  font-size: 16.5px;
}

.items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fff;
  transition: all 0.16s ease;
}

.item:hover {
  border-color: #c3ded5;
  background: #fcfefd;
}

.item-index {
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.item-main {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.item-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}

.item-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 0 0 auto;
}

.search-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.search-results {
  max-height: 46vh;
  overflow-y: auto;
  min-height: 80px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
}

.search-item + .search-item {
  margin-top: 8px;
}

.si-main {
  flex: 1;
  min-width: 0;
}

.si-title {
  margin: 0 0 3px;
  font-size: 14.5px;
  font-weight: 600;
}

.si-meta {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.empty-tip {
  text-align: center;
  font-size: 13px;
  padding: 20px 0;
}
</style>
