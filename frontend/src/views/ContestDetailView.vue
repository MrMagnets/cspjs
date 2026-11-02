<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contestApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const contest = ref(null)
const started = ref(false)
const answers = reactive({})
const remaining = ref(0)
const submitting = ref(false)
const warningCount = ref(0)
const result = ref(null)
const resultVisible = ref(false)
const editVisible = ref(false)
const savingEdit = ref(false)
const editForm = reactive({
  title: '',
  description: '',
  contest_type: 'official',
  start_at: null,
  end_at: null,
  duration_minutes: 120,
})
let timer = null
let lastCheatAt = 0
let forced = false
let suppressCheat = false

const submitted = computed(() => contest.value?.my_result?.status === 'submitted')
const active = computed(() => started.value && contest.value?.status === 'ongoing' && !submitted.value)
const canStart = computed(() => contest.value?.status === 'ongoing' && !submitted.value)
const countdownText = computed(() => {
  const s = Math.max(0, remaining.value)
  const h = String(Math.floor(s / 3600)).padStart(2, '0')
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const sec = String(s % 60).padStart(2, '0')
  return `${h}:${m}:${sec}`
})

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function tick() {
  if (!contest.value) return
  const now = Date.now()
  const end = new Date(contest.value.end_at).getTime()
  const start = new Date(contest.value.start_at).getTime()
  const target = now < start ? start : end
  remaining.value = Math.max(0, Math.floor((target - now) / 1000))
  if (remaining.value === 0 && now >= end && !submitted.value && !forced) {
    forced = true
    ElMessage.warning('比赛已结束，系统自动交卷')
    submit()
  }
}

async function reportCheat(event) {
  if (!active.value || forced || suppressCheat) return
  const now = Date.now()
  if (now - lastCheatAt < 1200) return
  lastCheatAt = now
  try {
    const res = await contestApi.antiCheat(contest.value.id, {
      event,
      detail: `page=${location.pathname}`,
    })
    warningCount.value = res.cheat_count
    if (res.force_submit) {
      forced = true
      await ElMessageBox.alert(res.message, '已强制交卷', { type: 'error', confirmButtonText: '知道了' })
      await submit()
    } else {
      ElMessage.warning(`${res.message}。第 3 次将强制交卷！`)
    }
  } catch (err) {
    ElMessage.error(err.message || '防作弊上报失败')
  }
}

function onVisibility() {
  if (document.visibilityState === 'hidden') reportCheat('visibilitychange')
}
function onBlur() {
  reportCheat('blur')
}

function attach() {
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('blur', onBlur)
  tick()
  timer = setInterval(tick, 1000)
}

function detach() {
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('blur', onBlur)
  if (timer) clearInterval(timer)
  timer = null
}

function begin() {
  if (!canStart.value) {
    ElMessage.warning(contest.value.status === 'upcoming' ? '比赛尚未开始' : '比赛已结束')
    return
  }
  started.value = true
  attach()
}

async function submit() {
  if (submitting.value || !contest.value) return
  if (!forced) {
    suppressCheat = true
    try {
      await ElMessageBox.confirm('交卷后不能再修改答案，确定交卷吗？', '确认交卷', {
        type: 'warning',
        confirmButtonText: '交卷',
        cancelButtonText: '再检查一下',
      })
    } catch {
      suppressCheat = false
      return
    }
  }
  submitting.value = true
  try {
    result.value = await contestApi.submit(contest.value.id, {
      answers: { ...answers },
      time_spent: Math.max(0, contest.value.duration_minutes * 60 - remaining.value),
    })
    contest.value.my_result = result.value
    resultVisible.value = true
    ElMessage.success(`交卷成功，得分 ${result.value.score}`)
    suppressCheat = true
    started.value = false
    detach()
  } catch (err) {
    ElMessage.error(err.message || '交卷失败')
  } finally {
    submitting.value = false
  }
}

function openEdit() {
  editForm.title = contest.value.title
  editForm.description = contest.value.description || ''
  editForm.contest_type = contest.value.contest_type
  editForm.start_at = new Date(contest.value.start_at)
  editForm.end_at = new Date(contest.value.end_at)
  editForm.duration_minutes = contest.value.duration_minutes
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.title.trim()) {
    ElMessage.warning('请填写比赛名称')
    return
  }
  savingEdit.value = true
  try {
    contest.value = await contestApi.update(contest.value.id, {
      title: editForm.title.trim(),
      description: editForm.description,
      contest_type: editForm.contest_type,
      start_at: new Date(editForm.start_at).toISOString(),
      end_at: new Date(editForm.end_at).toISOString(),
      duration_minutes: Number(editForm.duration_minutes) || 120,
    })
    editVisible.value = false
    ElMessage.success('比赛信息已更新')
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    savingEdit.value = false
  }
}

async function removeContest() {
  try {
    await ElMessageBox.confirm('删除后比赛及成绩将不可恢复，确定删除吗？', '删除比赛', {
      type: 'error',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await contestApi.remove(contest.value.id)
    ElMessage.success('比赛已删除')
    router.push({ name: 'contests' })
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

onMounted(async () => {
  try {
    contest.value = await contestApi.detail(route.params.id)
    warningCount.value = contest.value.my_result?.cheat_count || 0
  } catch (err) {
    ElMessage.error(err.message || '比赛加载失败')
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(detach)
</script>

<template>
  <div class="page contest-detail">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else-if="contest">
      <!-- 比赛说明页：先看说明，再进入赛场 -->
      <template v-if="!started">
        <section class="intro card">
          <div class="intro-top">
            <div class="head-tags">
              <el-tag :type="contest.contest_type === 'official' ? 'danger' : 'success'" effect="dark">
                {{ contest.contest_type === 'official' ? '官方赛' : '个人赛' }}
              </el-tag>
              <el-tag effect="plain">{{ contest.problem_count }} 题</el-tag>
              <el-tag :type="contest.status === 'ongoing' ? 'success' : 'info'" effect="plain">
                {{ contest.status === 'upcoming' ? '未开始' : contest.status === 'ongoing' ? '进行中' : '已结束' }}
              </el-tag>
            </div>
            <div class="intro-actions">
              <el-button v-if="auth.isAdmin" @click="openEdit">编辑</el-button>
              <el-button v-if="auth.isAdmin" type="danger" plain @click="removeContest">删除</el-button>
            </div>
          </div>

          <h1>{{ contest.title }}</h1>
          <div class="intro-meta">
            <span>开始：{{ fmt(contest.start_at) }}</span>
            <span>结束：{{ fmt(contest.end_at) }}</span>
            <span>时长：{{ contest.duration_minutes }} 分钟</span>
            <span>责任人：{{ contest.creator_name || '官方' }}</span>
            <span>参赛：{{ contest.participant_count }} 人</span>
          </div>

          <div class="intro-desc">
            <MarkdownView v-if="contest.description" :content="contest.description" />
            <p v-else class="muted">暂无比赛说明。</p>
          </div>

          <el-alert
            v-if="contest.my_result?.status === 'cheating'"
            type="error"
            :closable="false"
            show-icon
            title="系统已判定本场存在异常切屏，等待管理员复核；如有异议请到申诉中心提交录像。"
            class="tip"
          />
          <el-alert
            v-if="contest.my_result"
            type="success"
            :closable="false"
            show-icon
            :title="`已交卷，得分 ${contest.my_result.score}`"
            class="tip"
          />

          <div class="intro-foot">
            <el-button @click="router.push({ name: 'contests' })">返回比赛列表</el-button>
            <el-button
              v-if="!submitted"
              type="primary"
              size="large"
              :disabled="!canStart"
              @click="begin"
            >
              {{ contest.status === 'upcoming' ? '比赛尚未开始' : contest.status === 'ended' ? '比赛已结束' : '进入赛场' }}
            </el-button>
            <el-button v-else type="primary" size="large" @click="router.push({ name: 'contests' })">
              查看其他比赛
            </el-button>
          </div>
        </section>
      </template>

      <!-- 赛场 -->
      <template v-else>
        <div class="contest-head">
          <div>
            <div class="head-tags">
              <el-tag :type="contest.contest_type === 'official' ? 'danger' : 'success'" effect="dark">
                {{ contest.contest_type === 'official' ? '官方赛' : '个人赛' }}
              </el-tag>
              <el-tag effect="plain">{{ contest.problem_count }} 题</el-tag>
              <el-tag v-if="warningCount" type="warning" effect="plain">切屏警告 {{ warningCount }}/3</el-tag>
            </div>
            <h1>{{ contest.title }}</h1>
          </div>
          <div class="countdown" :class="{ danger: remaining < 300 }">
            <span>剩余时间</span>
            <strong>{{ countdownText }}</strong>
          </div>
        </div>

        <el-alert
          type="warning"
          :closable="false"
          show-icon
          title="防切屏已开启：切换标签页、最小化窗口或失去焦点都会被记录；第 3 次强制交卷。"
          class="anti-alert"
        />

        <div class="problem-list">
          <el-card v-for="(p, idx) in contest.problems" :key="p.problem_id" shadow="never" class="problem-card">
            <template #header>
              <div class="p-head">
                <span class="p-no">{{ idx + 1 }}</span>
                <strong>{{ p.title }}</strong>
                <el-tag size="small" effect="plain">{{ p.score }} 分</el-tag>
              </div>
            </template>
            <MarkdownView :content="p.content_md" />
            <div v-for="sq in p.sub_questions" :key="sq.id" class="sub-block">
              <div class="sub-title">第 {{ sq.order_no }} 小题</div>
              <MarkdownView :content="sq.content_md" />
              <el-radio-group v-model="answers[String(sq.id)]" :disabled="submitted || !active" class="options">
                <el-radio v-for="opt in sq.options" :key="opt.key" :value="opt.key" border>
                  <span class="opt-key">{{ opt.key }}</span>
                  <span class="opt-text"><MarkdownView :content="opt.text" /></span>
                </el-radio>
              </el-radio-group>
            </div>
          </el-card>
        </div>

        <div class="submit-bar">
          <span>已答 {{ Object.values(answers).filter(Boolean).length }} 小题</span>
          <el-button type="primary" size="large" :loading="submitting" :disabled="submitted || !active" @click="submit">
            交卷
          </el-button>
        </div>
      </template>

      <el-dialog v-model="resultVisible" title="交卷结果" width="420px">
        <div v-if="result" class="result-box">
          <div class="score">{{ result.score }}</div>
          <p>本场得分</p>
          <el-tag :type="result.status === 'cheating' ? 'danger' : 'success'">
            {{ result.status === 'cheating' ? '等待管理员复核' : '已提交' }}
          </el-tag>
        </div>
      </el-dialog>

      <el-dialog v-model="editVisible" title="编辑比赛" width="640px">
        <el-form label-width="90px">
          <el-form-item label="比赛名称">
            <el-input v-model="editForm.title" maxlength="200" show-word-limit />
          </el-form-item>
          <el-form-item label="比赛类型">
            <el-radio-group v-model="editForm.contest_type">
              <el-radio-button value="personal">个人赛</el-radio-button>
              <el-radio-button value="official">官方赛</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="开始时间">
            <el-date-picker v-model="editForm.start_at" type="datetime" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker v-model="editForm.end_at" type="datetime" style="width: 100%" />
          </el-form-item>
          <el-form-item label="时长">
            <el-input-number v-model="editForm.duration_minutes" :min="10" :max="600" /> 分钟
          </el-form-item>
          <el-form-item label="比赛说明">
            <el-input v-model="editForm.description" type="textarea" :rows="6" maxlength="4000" show-word-limit />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.contest-detail { max-width: 980px; margin: 0 auto; }
.intro { padding: 28px; border-radius: 18px; }
.intro-top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.intro h1 { margin: 14px 0 10px; font-size: 30px; }
.head-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.intro-meta { display: flex; flex-wrap: wrap; gap: 14px; color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.intro-desc { padding: 16px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.intro-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; gap: 12px; }
.tip { margin-top: 14px; border-radius: 10px; }
.contest-head { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.contest-head h1 { margin: 8px 0; font-size: 28px; }
.countdown { min-width: 170px; text-align: center; padding: 16px 20px; border-radius: 16px; background: #0f172a; color: #e2e8f0; }
.countdown span { display: block; font-size: 12px; opacity: .65; }
.countdown strong { font-size: 30px; letter-spacing: 1px; font-variant-numeric: tabular-nums; }
.countdown.danger { background: #7f1d1d; }
.anti-alert { margin: 18px 0; border-radius: 12px; }
.problem-list { display: grid; gap: 16px; }
.problem-card { border-radius: 16px; }
.p-head { display: flex; align-items: center; gap: 10px; }
.p-no { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; background: #eef4ff; color: #2563eb; font-weight: 700; }
.sub-block { margin-top: 18px; padding-top: 14px; border-top: 1px dashed var(--border); }
.sub-title { font-weight: 700; margin-bottom: 8px; }
.options { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.options :deep(.el-radio) { width: 100%; margin-right: 0; height: auto; padding: 10px 14px; align-items: flex-start; }
.opt-key { display: inline-grid; place-items: center; width: 22px; height: 22px; margin-right: 8px; border-radius: 6px; background: #eef4ff; color: #2563eb; font-weight: 700; flex: none; }
.opt-text { flex: 1; min-width: 0; }
.opt-text :deep(.markdown-body p) { margin: 0; }
.submit-bar { position: sticky; bottom: 16px; margin-top: 22px; padding: 14px 18px; border-radius: 14px; background: rgba(255,255,255,.94); backdrop-filter: blur(10px); border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 12px 30px rgba(31,45,70,.1); }
.result-box { text-align: center; }
.score { font-size: 56px; font-weight: 800; color: var(--accent); line-height: 1.1; }
@media (max-width: 760px) { .contest-head, .intro-top, .intro-foot { flex-direction: column; } .countdown { width: 100%; } }
</style>
