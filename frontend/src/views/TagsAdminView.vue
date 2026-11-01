<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { tagApi } from '@/api'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import EmptyState from '@/components/EmptyState.vue'

const { confirm } = useConfirmDialog()

const loading = ref(true)
const tags = ref([])
const submitting = ref(false)
const form = reactive({ name: '', category: '知识点' })

const grouped = computed(() => {
  const map = {}
  tags.value.forEach((tag) => {
    const key = tag.category || '其他'
    if (!map[key]) map[key] = []
    map[key].push(tag)
  })
  return map
})

async function load() {
  loading.value = true
  try {
    tags.value = await tagApi.list()
  } catch (err) {
    ElMessage.error(err.message || '标签加载失败')
  } finally {
    loading.value = false
  }
}

async function create() {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning('请输入标签名')
    return
  }
  submitting.value = true
  try {
    await tagApi.create({ name, category: form.category })
    ElMessage.success('标签已保存')
    form.name = ''
    await load()
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function remove(tag) {
  const ok = await confirm({
    title: '删除标签',
    message: `确定删除标签「${tag.name}」吗？该标签会从所有题目上移除。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await tagApi.remove(tag.id)
    ElMessage.success('已删除')
    await load()
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-title">
      标签管理
      <span class="sub">知识点标签用于统计诊断，来源标签用于分类检索</span>
    </div>

    <div class="card create-card">
      <h2 class="block-title">新建标签</h2>
      <div class="create-row">
        <el-input v-model="form.name" placeholder="标签名，例如：前缀和" maxlength="64" style="max-width: 260px" />
        <el-select v-model="form.category" style="width: 140px">
          <el-option label="知识点" value="知识点" />
          <el-option label="来源" value="来源" />
        </el-select>
        <el-button type="primary" :loading="submitting" @click="create">保存</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-for="(list, category) in grouped" :key="category" class="card group-card">
        <h2 class="block-title">
          {{ category }}
          <span class="muted count">{{ list.length }} 个</span>
        </h2>
        <div class="tag-list">
          <div v-for="tag in list" :key="tag.id" class="tag-item">
            <span>{{ tag.name }}</span>
            <button class="remove" @click="remove(tag)">×</button>
          </div>
        </div>
      </div>

      <EmptyState v-if="!loading && !tags.length" title="还没有标签" description="在上方新建第一个标签" />
    </div>
  </div>
</template>

<style scoped>
.create-card {
  margin-bottom: 16px;
}

.block-title {
  margin: 0 0 12px;
  font-size: 15.5px;
  font-weight: 700;
}

.count {
  font-size: 12.5px;
  font-weight: 400;
  margin-left: 6px;
}

.create-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.group-card + .group-card {
  margin-top: 14px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px 5px 13px;
  border-radius: 999px;
  background: #f2f5f8;
  border: 1px solid var(--border);
  font-size: 13px;
  color: #41525f;
}

.remove {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: #e2e8ef;
  color: #6b7c93;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.remove:hover {
  background: var(--bad);
  color: #fff;
}
</style>
