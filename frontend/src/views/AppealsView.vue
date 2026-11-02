<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { appealApi, contestApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import UserTitle from '@/components/UserTitle.vue'

const auth = useAuthStore()
const tab = ref('mine')
const loading = ref(true)
const mine = ref([])
const all = ref([])
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ contest_id: null, reason: '', video_url: '' })

const statusMeta = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '申诉通过', type: 'success' },
  rejected: { label: '申诉驳回', type: 'danger' },
}

const list = computed(() => (tab.value === 'mine' ? mine : all))

async function load() {
  loading.value = true
  try {
    mine.value = (await appealApi.mine()) || []
    if (auth.isAdmin) all.value = (await appealApi.all()) || []
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.reason.trim() || !form.video_url.trim()) {
    ElMessage.warning('请填写申诉理由和录像链接')
    return
  }
  saving.value = true
  try {
    await appealApi.create({ ...form, contest_id: form.contest_id || null })
    ElMessage.success('申诉已提交，请等待管理员审核')
    dialog.value = false
    form.reason = ''
    form.video_url = ''
    await load()
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    saving.value = false
  }
}

async function review(row, action) {
  let note = ''
  try {
    const res = await ElMessageBox.prompt(
      action === 'approve' ? '通过后账号恢复正常、信用分恢复 100。可填写备注：' : '填写驳回原因：',
      action === 'approve' ? '通过申诉' : '驳回申诉',
      { inputType: 'textarea', inputPlaceholder: '可选', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
    note = res.value || ''
  } catch {
    return
  }
  try {
    await appealApi.review(row.id, { action, note })
    ElMessage.success('处理完成')
    await load()
  } catch (err) {
    ElMessage.error(err.message || '处理失败')
  }
}

async function judgeCheat(row) {
  if (!row.contest_id) {
    ElMessage.warning('该申诉没有关联比赛，请到用户管理中直接封禁')
    return
  }
  try {
    await ElMessageBox.confirm('将封禁该用户、清零小猴值、信用分设 50、标记棕名并关闭出题权限。确定吗？', '判定作弊', {
      type: 'error',
      confirmButtonText: '判定作弊',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await contestApi.judge(row.contest_id, { user_id: row.user_id, cheat: true, severe: true, reason: '申诉复核维持作弊判定' })
    await appealApi.review(row.id, { action: 'reject', note: '申诉驳回：管理员复核维持作弊判定' })
    ElMessage.warning('已判定作弊并驳回申诉')
    await load()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { hour12: false }) : '—'
}

onMounted(load)
</script>

<template>
  <div class="page appeals-page">
    <div class="page-title">
      申诉中心
      <span class="sub">提交完整录像链接，管理员复核作弊判定</span>
      <span class="spacer" />
      <el-button type="primary" @click="dialog = true">提交申诉</el-button>
    </div>

    <el-tabs v-if="auth.isAdmin" v-model="tab">
      <el-tab-pane label="我的申诉" name="mine" />
      <el-tab-pane label="全部申诉（管理员）" name="all" />
    </el-tabs>

    <el-skeleton v-if="loading" :rows="5" animated />
    <div v-else class="appeal-list">
      <article v-for="a in list" :key="a.id" class="appeal card">
        <div class="a-head">
          <el-tag :type="statusMeta[a.status]?.type" effect="dark">{{ statusMeta[a.status]?.label || a.status }}</el-tag>
          <strong>{{ a.username || '未知用户' }}</strong>
          <UserTitle :user="{ role: 'user', title: a.title }" />
          <span v-if="a.user_id" class="muted">#{{ a.user_id }}</span>
          <span class="time">{{ fmt(a.created_at) }}</span>
        </div>
        <p class="reason">{{ a.reason }}</p>
        <a class="video" :href="a.video_url" target="_blank" rel="noopener noreferrer">查看录像 ↗</a>
        <p v-if="a.admin_note" class="note">管理员备注：{{ a.admin_note }}</p>
        <div v-if="auth.isAdmin && a.status === 'pending'" class="a-actions">
          <el-button type="success" size="small" @click="review(a, 'approve')">通过并解封</el-button>
          <el-button v-if="a.contest_id" type="danger" size="small" plain @click="judgeCheat(a)">判定作弊</el-button>
          <el-button type="warning" size="small" plain @click="review(a, 'reject')">驳回</el-button>
        </div>
      </article>
      <el-empty v-if="!list.length" description="暂无申诉记录" />
    </div>

    <el-dialog v-model="dialog" title="提交申诉" width="620px">
      <el-form label-width="90px">
        <el-form-item label="比赛 ID">
          <el-input-number v-model="form.contest_id" :min="1" placeholder="可选" />
        </el-form-item>
        <el-form-item label="录像链接">
          <el-input v-model="form.video_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="申诉理由">
          <el-input v-model="form.reason" type="textarea" :rows="5" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.appeals-page { max-width: 900px; margin: 0 auto; }
.appeal-list { display: grid; gap: 12px; }
.appeal { padding: 18px; border-radius: 14px; }
.a-head { display: flex; align-items: center; gap: 10px; }
.a-head .time { margin-left: auto; color: var(--muted); font-size: 12px; }
.muted { color: var(--muted); font-size: 12px; }
.reason { margin: 12px 0 8px; white-space: pre-wrap; }
.video { color: #2563eb; font-size: 13px; }
.note { margin-top: 10px; padding: 8px 10px; border-radius: 8px; background: #f7f9fd; color: var(--muted); font-size: 13px; }
.a-actions { margin-top: 12px; display: flex; gap: 8px; }
</style>
