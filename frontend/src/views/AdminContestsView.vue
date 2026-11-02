<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contestApi } from '@/api'

const loading = ref(true)
const contests = ref([])
const dialog = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive({
  title: '',
  description: '',
  contest_type: 'official',
  start_at: null,
  end_at: null,
  duration_minutes: 120,
})

const statusMeta = {
  upcoming: { label: '未开始', type: 'info' },
  ongoing: { label: '进行中', type: 'success' },
  ended: { label: '已结束', type: 'info' },
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { hour12: false }) : '—'
}

async function load() {
  loading.value = true
  try {
    contests.value = (await contestApi.list()) || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.contest_type = 'official'
  form.start_at = new Date(Date.now() + 60 * 60 * 1000)
  form.end_at = new Date(Date.now() + 3 * 60 * 60 * 1000)
  form.duration_minutes = 120
  dialog.value = true
}

async function openEdit(row) {
  editingId.value = row.id
  try {
    const detail = await contestApi.detail(row.id)
    form.title = detail.title
    form.description = detail.description || ''
    form.contest_type = detail.contest_type
    form.start_at = new Date(detail.start_at)
    form.end_at = new Date(detail.end_at)
    form.duration_minutes = detail.duration_minutes
    dialog.value = true
  } catch (err) {
    ElMessage.error(err.message || '比赛加载失败')
  }
}

async function save() {
  if (!form.title.trim() || !form.start_at || !form.end_at) {
    ElMessage.warning('请填写完整比赛信息')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      description: form.description,
      contest_type: form.contest_type,
      start_at: new Date(form.start_at).toISOString(),
      end_at: new Date(form.end_at).toISOString(),
      duration_minutes: Number(form.duration_minutes) || 120,
    }
    if (editingId.value) {
      await contestApi.update(editingId.value, payload)
    } else {
      await contestApi.create({ ...payload, problems: [] })
    }
    ElMessage.success(editingId.value ? '比赛已更新' : '比赛已创建')
    dialog.value = false
    await load()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？成绩与题目关联会一并删除。`, '删除比赛', {
      type: 'error',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await contestApi.remove(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-contests">
    <div class="head">
      <h2>比赛管理</h2>
      <el-button type="primary" @click="openCreate">新建比赛</el-button>
    </div>

    <el-table v-loading="loading" :data="contests" stripe>
      <el-table-column prop="title" label="比赛" min-width="200" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.contest_type === 'official' ? 'danger' : 'success'" size="small" effect="plain">
            {{ row.contest_type === 'official' ? '官方赛' : '个人赛' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMeta[row.status]?.type" size="small">{{ statusMeta[row.status]?.label || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始" width="170">
        <template #default="{ row }">{{ fmt(row.start_at) }}</template>
      </el-table-column>
      <el-table-column label="结束" width="170">
        <template #default="{ row }">{{ fmt(row.end_at) }}</template>
      </el-table-column>
      <el-table-column prop="problem_count" label="题数" width="70" />
      <el-table-column prop="participant_count" label="人数" width="70" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑比赛' : '新建比赛'" width="620px">
      <el-form label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.contest_type">
            <el-radio-button value="official">官方赛</el-radio-button>
            <el-radio-button value="personal">个人赛</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始">
          <el-date-picker v-model="form.start_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束">
          <el-date-picker v-model="form.end_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时长">
          <el-input-number v-model="form.duration_minutes" :min="10" :max="600" /> 分钟
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="5" maxlength="4000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.head h2 { margin: 0; font-size: 20px; }
</style>
