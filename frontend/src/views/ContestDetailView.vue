<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contestApi } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const loading = ref(true)
const contest = ref(null)
const answers = reactive({})
const remaining = ref(0)
const submitting = ref(false)
const warningCount = ref(0)
const result = ref(null)
const resultVisible = ref(false)
let timer = null
let lastCheatAt = 0
let forced = false
let suppressCheat = false

const submitted = computed(() => contest.value?.my_result?.status === 'submitted')
const active = computed(() => contest.value?.status === 'ongoing' && !submitted.value)
const countdownText = computed(() => {
  const s = Math.max(0, remaining.value)
  const h = String(Math.floor(s / 3600)).padStart(2, '0')
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const sec = String(s % 60).padStart(2, '0')
  return `${h}:${m}:${sec}`
})

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
    detach()
  } catch (err) {
    ElMessage.error(err.message || '交卷失败')
  } finally {
    submitting.value = false
  }
}

function detach() {
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('blur', onBlur)
  if (timer) clearInterval(timer)
}

onMounted(async () => {
  try {
    contest.value = await contestApi.detail(route.params.id)
    warningCount.value = contest.value.my_result?.cheat_count || 0
    tick()
    timer = setInterval(tick, 1000)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
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
          <p class="desc">{{ contest.description || '认真作答，切屏超过 3 次将被强制交卷。' }}</p>
        </div>
        <div class="countdown" :class="{ danger: remaining < 300 }">
          <span>剩余时间</span>
          <strong>{{ countdownText }}</strong>
        </div>
      </div>

      <el-alert
        v-if="active"
        type="warning"
        :closable="false"
        show-icon
        title="防切屏已开启：切换标签页、最小化窗口或失去焦点都会被记录；第 3 次强制交卷。"
        class="anti-alert"
      />
      <el-alert
        v-if="contest.my_result?.status === 'cheating'"
        type="error"
        :closable="false"
        show-icon
        title="系统已判定本场存在异常切屏，等待管理员复核；如有异议请到申诉中心提交录像。"
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
                <span class="opt-key">{{ opt.key }}</span>{{ opt.text }}
              </el-radio>
            </el-radio-group>
          </div>
        </el-card>
      </div>

      <div class="submit-bar">
        <span v-if="submitted">已交卷 · 得分 {{ contest.my_result.score }}</span>
        <span v-else>已答 {{ Object.values(answers).filter(Boolean).length }} 小题</span>
        <el-button type="primary" size="large" :loading="submitting" :disabled="submitted || !active" @click="submit">
          交卷
        </el-button>
      </div>

      <el-dialog v-model="resultVisible" title="交卷结果" width="420px">
        <div v-if="result" class="result-box">
          <div class="score">{{ result.score }}</div>
          <p>本场得分</p>
          <el-tag :type="result.status === 'cheating' ? 'danger' : 'success'">
            {{ result.status === 'cheating' ? '等待管理员复核' : '已提交' }}
          </el-tag>
        </div>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.contest-detail { max-width: 980px; margin: 0 auto; }
.contest-head { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.head-tags { display: flex; gap: 8px; margin-bottom: 10px; }
.contest-head h1 { margin: 0 0 8px; font-size: 28px; }
.desc { color: var(--muted); margin: 0; max-width: 640px; }
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
.options :deep(.el-radio) { width: 100%; margin-right: 0; height: auto; padding: 10px 14px; }
.opt-key { display: inline-grid; place-items: center; width: 22px; height: 22px; margin-right: 8px; border-radius: 6px; background: #eef4ff; color: #2563eb; font-weight: 700; }
.submit-bar { position: sticky; bottom: 16px; margin-top: 22px; padding: 14px 18px; border-radius: 14px; background: rgba(255,255,255,.94); backdrop-filter: blur(10px); border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 12px 30px rgba(31,45,70,.1); }
.result-box { text-align: center; }
.score { font-size: 56px; font-weight: 800; color: var(--accent); line-height: 1.1; }
@media (max-width: 760px) { .contest-head { flex-direction: column; } .countdown { width: 100%; } }
</style>
