<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { auditApi } from '@/api'

const loading = ref(true)
const rows = ref([])

const labels = {
  ban_user: '封禁用户',
  unban_user: '解封用户',
  toggle_create_problem: '出题权限',
  avatar_review: '头像审核',
  update_contest: '修改比赛',
  delete_contest: '删除比赛',
  judge_contest: '比赛判定',
  appeal_approve: '申诉通过',
  appeal_reject: '申诉驳回',
  pin_discussion: '讨论置顶',
}

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  try {
    rows.value = (await auditApi.list()) || []
  } catch (err) {
    ElMessage.error(err.message || '日志加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="admin-audit">
    <div class="head">
      <h2>陶片放逐 · 操作审计</h2>
      <span class="muted">最近 200 条管理员操作</span>
    </div>
    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="管理员" width="140">
        <template #default="{ row }">{{ row.admin_name || '系统' }}</template>
      </el-table-column>
      <el-table-column label="动作" width="130">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ labels[row.action] || row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="对象" width="150">
        <template #default="{ row }">{{ row.target_type }} #{{ row.target_id ?? '—' }}</template>
      </el-table-column>
      <el-table-column prop="detail" label="详情" min-width="260" show-overflow-tooltip />
    </el-table>
    <el-empty v-if="!loading && !rows.length" description="暂无审计记录" />
  </div>
</template>

<style scoped>
.head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.head h2 { margin: 0; font-size: 20px; }
.muted { color: var(--muted); font-size: 12px; }
</style>
