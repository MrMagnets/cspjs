<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const lists = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const form = reactive({ title: '', description: '', is_public: true })

async function load() {
  loading.value = true
  try {
    lists.value = await listApi.list({ scope: auth.isLoggedIn ? 'visible' : 'public' })
  } catch (err) {
    ElMessage.error(err.message || '题单加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后才能创建题单')
    router.push({ name: 'login', query: { redirect: '/lists' } })
    return
  }
  form.title = ''
  form.description = ''
  form.is_public = true
  dialogVisible.value = true
}

async function create() {
  if (form.title.trim().length < 1) {
    ElMessage.warning('请填写题单标题')
    return
  }
  saving.value = true
  try {
    const created = await listApi.create({
      title: form.title.trim(),
      description: form.description,
      is_public: form.is_public,
    })
    ElMessage.success('题单已创建')
    dialogVisible.value = false
    await load()
    router.push({ name: 'list-detail', params: { id: created.id } })
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-title">
      题单
      <span class="sub">按顺序练习</span>
      <span class="spacer" />
      <el-button type="primary" @click="openCreate">新建题单</el-button>
    </div>

    <div v-loading="loading" class="list-grid">
      <article
        v-for="list in lists"
        :key="list.id"
        class="list-card"
        @click="router.push({ name: 'list-detail', params: { id: list.id } })"
      >
        <div class="lc-head">
          <span class="lc-title">{{ list.title }}</span>
          <el-tag size="small" :type="list.is_public ? 'success' : 'info'" effect="plain">
            {{ list.is_public ? '公开' : '私有' }}
          </el-tag>
        </div>
        <p class="lc-desc">{{ list.description || '暂无描述' }}</p>
        <div class="lc-foot">
          <span class="lc-count">{{ list.problem_count }} 题</span>
          <span class="dot-sep">·</span>
          <span>{{ list.creator_name || '匿名' }}</span>
          <span class="dot-sep">·</span>
          <span>{{ formatDate(list.created_at) }}</span>
        </div>
      </article>
    </div>

    <EmptyState
      v-if="!loading && !lists.length"
      title="还没有题单"
      description="创建一个题单，把想刷的题目按顺序收集起来。"
      :action-text="auth.isLoggedIn ? '新建题单' : '登录后创建'"
      @action="openCreate"
    />

    <el-dialog v-model="dialogVisible" title="新建题单" width="480px" align-center>
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" placeholder="例如：初赛必刷 20 题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="这个题单覆盖哪些考点？" />
        </el-form-item>
        <el-form-item label="可见性">
          <el-switch v-model="form.is_public" active-text="公开" inactive-text="私有" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.list-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  min-height: 100px;
}

@media (max-width: 1000px) {
  .list-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .list-grid {
    grid-template-columns: 1fr;
  }
}

.list-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 140px;
}

.list-card:hover {
  border-color: #c3ded5;
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.lc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.lc-title {
  font-size: 16px;
  font-weight: 650;
  line-height: 1.5;
}

.lc-desc {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lc-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--muted);
}

.lc-count {
  color: var(--brand-dark);
  font-weight: 600;
}

.dot-sep {
  color: #c8d2dd;
}
</style>
