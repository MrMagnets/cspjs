<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminUserApi } from '@/api'

const loading = ref(true)
const keyword = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const updating = ref(null)

async function load() {
  loading.value = true
  try {
    const data = await adminUserApi.list({ search: keyword.value, page: page.value, page_size: pageSize })
    rows.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function unban(row) {
  updating.value = row.id
  try {
    const updated = await adminUserApi.unban(row.id)
    Object.assign(row, updated)
    ElMessage.success(`${row.username} 已解封，信用分恢复 100`)
  } catch (err) {
    ElMessage.error(err.message || '解封失败')
  } finally {
    updating.value = null
  }
}

async function toggle(row, enabled) {
  updating.value = row.id
  try {
    const updated = await adminUserApi.toggleCreate(row.id, enabled)
    Object.assign(row, updated)
    ElMessage.success(enabled ? '已恢复出题权限' : '已禁用出题权限')
  } catch (err) {
    row.can_create_problem = !enabled
    ElMessage.error(err.message || '操作失败')
  } finally {
    updating.value = null
  }
}

async function ban(row) {
  updating.value = row.id
  try {
    const updated = await adminUserApi.ban(row.id)
    Object.assign(row, updated)
    ElMessage.warning(`${row.username} 已被封禁`)
  } catch (err) {
    ElMessage.error(err.message || '封禁失败')
  } finally {
    updating.value = null
  }
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleDateString('zh-CN') : '—'
}

function search() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="page admin-users">
    <div class="page-title">
      用户管理
      <span class="sub">搜索用户、解封、控制出题权限</span>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名 / 称号" clearable style="max-width: 320px" @keyup.enter="search" />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="用户" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="32">{{ row.username.slice(0, 1).toUpperCase() }}</el-avatar>
              <div>
                <div :class="{ brown: row.title.includes('棕') }">{{ row.username }}</div>
                <small class="muted">#{{ row.id }} · {{ fmt(row.created_at) }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="称号" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.title" :type="row.title.includes('棕') ? 'danger' : 'warning'" effect="plain">
              {{ row.title }}
            </el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'banned' ? 'danger' : 'success'" effect="dark">
              {{ row.status === 'banned' ? '已封禁' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="credit_score" label="信用分" width="90" />
        <el-table-column prop="monkey_score" label="小猴值" width="90" />
        <el-table-column label="出题权限" width="130">
          <template #default="{ row }">
            <el-switch
              :model-value="row.can_create_problem"
              :loading="updating === row.id"
              inline-prompt
              active-text="允许"
              inactive-text="禁用"
              @change="(v) => toggle(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'banned'"
              type="danger"
              size="small"
              :loading="updating === row.id"
              @click="unban(row)"
            >
              解封
            </el-button>
            <el-button v-else type="warning" size="small" plain @click="ban(row)">封禁</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.admin-users { max-width: 1080px; margin: 0 auto; }
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.user-cell { display: flex; align-items: center; gap: 10px; }
.muted { color: var(--muted); }
.brown { color: #8b5a2b; font-weight: 700; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
