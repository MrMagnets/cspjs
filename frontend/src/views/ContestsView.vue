<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { contestApi } from '@/api'

const router = useRouter()
const loading = ref(true)
const tab = ref('all')
const contests = ref([])

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
