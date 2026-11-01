<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { problemApi } from '@/api'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import ProblemCard from '@/components/ProblemCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const { confirm } = useConfirmDialog()

const loading = ref(true)
const problems = ref([])
const activeStatus = ref('all')

const TABS = [
  { name: 'all', label: '全部' },
  { name: 'pending', label: '待审核' },
  { name: 'approved', label: '已通过' },
  { name: 'rejected', label: '已驳回' },
]

const counts = computed(() => {
  const map = { all: problems.value.length, pending: 0, approved: 0, rejected: 0 }
  problems.value.forEach((p) => {
    map[p.status] = (map[p.status] || 0) + 1
  })
  return map
})

const visible = computed(() =>
  activeStatus.value === 'all' ? problems.value : problems.value.filter((p) => p.status === activeStatus.value),
)

async function load() {
  loading.value = true
  try {
    const data = await problemApi.list({ status: 'mine', page_size: 50 })
    problems.value = data.items
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function edit(problem) {
  router.push({ name: 'problem-edit', params: { id: problem.id } })
}

async function remove(problem) {
  const ok = await confirm({
    title: '删除题目',
    message: `确定删除《${problem.title}》吗？删除后不可恢复。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await problemApi.remove(problem.id)
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
      我的投稿
      <span class="sub">共 {{ problems.length }} 道</span>
      <span class="spacer" />
      <el-button type="primary" @click="router.push({ name: 'problem-create' })">投稿新题目</el-button>
    </div>

    <div class="tabs">
      <button
        v-for="tab in TABS"
        :key="tab.name"
        class="tab"
        :class="{ active: activeStatus === tab.name }"
        @click="activeStatus = tab.name"
      >
        {{ tab.label }}
        <span class="tab-count">{{ counts[tab.name] || 0 }}</span>
      </button>
    </div>

    <div v-loading="loading" class="list-grid">
      <div v-for="problem in visible" :key="problem.id" class="item">
        <ProblemCard :problem="problem" show-status />
        <div class="item-actions">
          <el-button
            size="small"
            :disabled="problem.status === 'approved'"
            @click="edit(problem)"
          >
            编辑
          </el-button>
          <el-button size="small" type="danger" plain @click="remove(problem)">删除</el-button>
          <el-button size="small" link type="primary" @click="router.push({ name: 'problem-detail', params: { id: problem.id } })">
            查看详情
          </el-button>
        </div>
      </div>
    </div>

    <EmptyState
      v-if="!loading && !visible.length"
      :title="problems.length ? '该状态下暂无题目' : '还没有投稿记录'"
      description="投稿后进入待审核队列，管理员通过后即可公开。"
      action-text="去投稿"
      @action="router.push({ name: 'problem-create' })"
    />
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
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
  transition: all 0.16s ease;
}

.tab:hover {
  border-color: #b9d6cd;
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

.list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-height: 100px;
}

.item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-actions {
  display: flex;
  gap: 8px;
  padding: 0 4px;
}

@media (max-width: 900px) {
  .list-grid {
    grid-template-columns: 1fr;
  }
}
</style>
