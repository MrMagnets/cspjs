<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contestApi, problemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const tab = ref('all')
const contests = ref([])
const createVisible = ref(false)
const creating = ref(false)
const problemOptions = ref([])
const form = reactive({
  title: '',
  description: '',
  contest_type: 'official',
  start_at: null,
  end_at: null,
  duration_minutes: 120,
  problem_ids: [],
})

const canCreate = computed(() => auth.isLoggedIn)

const filtered = computed(() =>
  tab.value === 'all' ? contests.value : contests.value.filter((c) => c.contest_type === tab.value),
)

const statusMeta = {
  upcoming: { label: '即将开始', type: 'info' },
  ongoing: { label: '进行中', type: 'success' },
  ended: { label: '已结束', type: 'info' },
}

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

function openCreate() {
  const start = new Date(Date.now() + 60 * 60 * 1000)
  const end = new Date(Date.now() + 3 * 60 * 60 * 1000)
  form.title = ''
  form.description = ''
  form.contest_type = auth.isAdmin ? 'official' : 'personal'
  form.start_at = start
  form.end_at = end
  form.duration_minutes = 120
  form.problem_ids = []
  createVisible.value = true
  if (!problemOptions.value.length) {
    problemApi.list({ page_size: 50, status: 'approved' }).then((data) => {
      problemOptions.value = data.items || []
    }).catch(() => {})
  }
}

async function createContest() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写比赛名称')
    return
  }
  if (!form.start_at || !form.end_at) {
    ElMessage.warning('请选择开始和结束时间')
    return
  }
  if (new Date(form.end_at) <= new Date(form.start_at)) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }
  creating.value = true
  try {
    const created = await contestApi.create({
      title: form.title.trim(),
      description: form.description,
      contest_type: form.contest_type,
      start_at: new Date(form.start_at).toISOString(),
      end_at: new Date(form.end_at).toISOString(),
      duration_minutes: Number(form.duration_minutes) || 120,
      problems: form.problem_ids.map((id, index) => ({
        problem_id: id,
        order_no: index + 1,
        score: 10,
      })),
    })
    ElMessage.success('比赛已创建')
    createVisible.value = false
    router.push({ name: 'contest-detail', params: { id: created.id } })
  } catch (err) {
    ElMessage.error(err.message || '创建比赛失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    contests.value = (await contestApi.list()) || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page contests-page">
    <div class="page-title">
      比赛中心
      <span class="sub">官方赛计入小猴值 · 个人赛仅供练习</span>
      <span class="spacer" />
      <el-button v-if="canCreate" type="primary" @click="openCreate">发起比赛</el-button>
    </div>

    <el-tabs v-model="tab" class="contest-tabs">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="官方赛" name="official" />
      <el-tab-pane label="个人赛" name="personal" />
    </el-tabs>

    <el-skeleton v-if="loading" :rows="6" animated />
    <div v-else-if="filtered.length" class="contest-grid">
      <article
        v-for="c in filtered"
        :key="c.id"
        class="contest-card"
        :class="c.contest_type"
        @click="router.push({ name: 'contest-detail', params: { id: c.id } })"
      >
        <div class="cc-top">
          <span class="type-dot" />
          <el-tag size="small" effect="plain" :type="c.contest_type === 'official' ? 'danger' : 'success'">
            {{ c.contest_type === 'official' ? '官方赛' : '个人赛' }}
          </el-tag>
          <el-tag size="small" :type="statusMeta[c.status]?.type" effect="dark">
            {{ statusMeta[c.status]?.label || c.status }}
          </el-tag>
        </div>
        <h3>{{ c.title }}</h3>
        <div class="cc-meta">
          <span>开始 {{ fmt(c.start_at) }}</span>
          <span>时长 {{ c.duration_minutes }} 分钟</span>
          <span>题量 {{ c.problem_count }} 题</span>
        </div>
        <div class="cc-foot">
          <span class="participants">{{ c.participant_count }} 人参赛</span>
          <el-button type="primary" text>进入赛场 →</el-button>
        </div>
      </article>
    </div>
    <el-empty v-else description="暂无比赛，稍后再来看看" />

    <el-dialog v-model="createVisible" title="发起比赛" width="680px" top="6vh">
      <el-form label-width="90px">
        <el-form-item label="比赛名称">
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="例如：2026 CSP-J 模拟赛" />
        </el-form-item>
        <el-form-item label="比赛类型">
          <el-radio-group v-model="form.contest_type">
            <el-radio-button value="personal">个人赛（不计小猴值）</el-radio-button>
            <el-radio-button value="official" :disabled="!auth.isAdmin">申办官方赛（仅管理员）</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="比赛时长">
          <el-input-number v-model="form.duration_minutes" :min="10" :max="600" /> 分钟
        </el-form-item>
        <el-form-item label="选择题目">
          <el-select v-model="form.problem_ids" multiple filterable style="width: 100%" placeholder="可留空，稍后配置">
            <el-option
              v-for="p in problemOptions"
              :key="p.id"
              :label="`${p.problem_number || p.id} · ${p.title}`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="比赛说明">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createContest">创建比赛</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.contests-page { max-width: 1080px; margin: 0 auto; }
.contest-tabs { margin-bottom: 14px; }
.contest-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }
.contest-card {
  position: relative; padding: 20px; border-radius: 18px; cursor: pointer;
  background: linear-gradient(150deg, #fff, #f7f9fd);
  border: 1px solid var(--border);
  box-shadow: 0 10px 30px rgba(31,45,70,.05);
  transition: transform .2s, box-shadow .2s;
  overflow: hidden;
}
.contest-card::after {
  content: ''; position: absolute; right: -40px; top: -40px; width: 130px; height: 130px;
  border-radius: 50%; background: radial-gradient(circle, rgba(64,158,255,.12), transparent 70%);
}
.contest-card.official::after { background: radial-gradient(circle, rgba(245,108,108,.14), transparent 70%); }
.contest-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(31,45,70,.12); }
.cc-top { display: flex; align-items: center; gap: 8px; }
.type-dot { width: 8px; height: 8px; border-radius: 50%; background: #409eff; }
.contest-card.official .type-dot { background: #f56c6c; }
.contest-card h3 { margin: 14px 0 10px; font-size: 19px; color: var(--text-strong); }
.cc-meta { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--muted); }
.cc-meta span { display: inline-flex; align-items: center; gap: 4px; }
.cc-foot { margin-top: 18px; padding-top: 12px; border-top: 1px dashed var(--border); display: flex; justify-content: space-between; align-items: center; }
.participants { font-size: 12px; color: var(--muted); }
</style>
