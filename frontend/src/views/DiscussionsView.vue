<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { discussionApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const category = ref('全部')
const items = ref([])
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ title: '', content_md: '', category: '学术', problem_id: null })

const categories = ['全部', '站务', '学术', '题目']
const canPost = computed(() => auth.isLoggedIn)

async function load() {
  loading.value = true
  try {
    items.value = (await discussionApi.list(category.value === '全部' ? {} : { category: category.value })) || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.title = ''
  form.content_md = ''
  form.category = auth.isAdmin ? '站务' : '学术'
  form.problem_id = null
  dialog.value = true
}

async function create() {
  if (!form.title.trim() || !form.content_md.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  saving.value = true
  try {
    const created = await discussionApi.create({ ...form, problem_id: form.problem_id || null })
    ElMessage.success('发帖成功')
    dialog.value = false
    router.push({ name: 'discussion-detail', params: { id: created.id } })
  } catch (err) {
    ElMessage.error(err.message || '发帖失败')
  } finally {
    saving.value = false
  }
}

async function pinThread(item, event) {
  event?.stopPropagation()
  try {
    const updated = await discussionApi.pin(item.id, !item.is_pinned)
    item.is_pinned = updated.is_pinned
    ElMessage.success(item.is_pinned ? '已置顶' : '已取消置顶')
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<template>
  <div class="page discussions-page">
    <div class="page-title">
      讨论区
      <span class="sub">站务公告 · 学术交流 · 题目讨论</span>
      <span class="spacer" />
      <el-button v-if="canPost" type="primary" @click="openCreate">发布帖子</el-button>
    </div>

    <el-tabs v-model="category" @tab-change="load">
      <el-tab-pane v-for="c in categories" :key="c" :label="c" :name="c" />
    </el-tabs>

    <el-skeleton v-if="loading" :rows="6" animated />
    <div v-else class="thread-list">
      <article v-for="d in items" :key="d.id" class="thread" @click="router.push({ name: 'discussion-detail', params: { id: d.id } })">
        <div class="thread-avatar">{{ d.author_name?.slice(0, 1) || '?' }}</div>
        <div class="thread-body">
          <div class="thread-title">
            <el-tag v-if="d.is_pinned" size="small" type="danger" effect="dark">置顶</el-tag>
            <el-tag v-if="d.is_locked" size="small" type="info">已锁定</el-tag>
            <el-tag size="small" :type="d.category === '站务' ? 'danger' : d.category === '题目' ? 'warning' : 'success'" effect="plain">
              {{ d.category }}
            </el-tag>
            <strong>{{ d.title }}</strong>
          </div>
          <div class="thread-meta">
            {{ d.author_name }} · {{ fmt(d.created_at) }} · {{ d.comment_count }} 条回复
          </div>
        </div>
        <span class="arrow">›</span>
        <el-button v-if="auth.isAdmin" size="small" :type="d.is_pinned ? 'warning' : 'default'" text @click.stop="pinThread(d, $event)">
          {{ d.is_pinned ? '取消置顶' : '置顶' }}
        </el-button>
      </article>
      <el-empty v-if="!items.length" description="这个分类还没有帖子" />
    </div>

    <el-dialog v-model="dialog" title="发布帖子" width="760px" top="6vh">
      <el-form label-width="70px">
        <el-form-item label="分类">
          <el-radio-group v-model="form.category">
            <el-radio-button v-if="auth.isAdmin" value="站务">站务</el-radio-button>
            <el-radio-button value="学术">学术</el-radio-button>
            <el-radio-button value="题目">题目</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <MarkdownEditor v-model="form.content_md" :rows="10" show-tip />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.discussions-page { max-width: 980px; margin: 0 auto; }
.thread-list { display: grid; gap: 10px; }
.thread { display: flex; align-items: center; gap: 14px; padding: 16px 18px; border-radius: 14px; border: 1px solid var(--border); background: #fff; cursor: pointer; transition: .2s; }
.thread:hover { border-color: #b9d4ff; box-shadow: 0 8px 24px rgba(37,99,235,.08); transform: translateY(-1px); }
.thread-avatar { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg, #dbeafe, #eff6ff); color: #2563eb; font-weight: 700; }
.thread-body { flex: 1; min-width: 0; }
.thread-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.thread-title strong { font-size: 16px; }
.thread-meta { color: var(--muted); font-size: 12px; margin-top: 5px; }
.arrow { color: #b6c2d4; }
</style>
