<script setup>
import { computed, onMounted, ref } from 'vue'
import { rankingApi } from '@/api'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(true)
const rows = ref([])
const podium = computed(() => rows.value.slice(0, 3))
const rest = computed(() => rows.value.slice(3))

const medal = {
  1: { label: '冠军', color: '#f6c453', glow: 'rgba(246,196,83,.35)' },
  2: { label: '亚军', color: '#c7d2e0', glow: 'rgba(199,210,224,.3)' },
  3: { label: '季军', color: '#d99a6c', glow: 'rgba(217,154,108,.3)' },
}

function titleClass(title) {
  if (!title) return ''
  if (title.includes('棕')) return 'brown'
  if (title.includes('金')) return 'gold'
  return 'custom'
}

onMounted(async () => {
  try {
    rows.value = (await rankingApi.list({ limit: 50 })) || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page ranking-page">
    <div class="page-title">
      小猴排行榜
      <span class="sub">按小猴值排序 · 官方赛成绩计入</span>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else>
      <section v-if="podium.length" class="podium-wrap">
        <div class="podium-glow" />
        <div class="podium">
          <article
            v-for="(item, idx) in [podium[1], podium[0], podium[2]]"
            :key="item?.user_id"
            class="podium-item"
            :class="`place-${item?.rank || idx + 1}`"
          >
            <div v-if="item" class="winner">
              <svg v-if="item.rank === 1" class="crown" viewBox="0 0 64 40" aria-hidden="true">
                <path d="M6 32 3 9l16 10L32 3l13 16L61 9l-3 23H6Z" fill="url(#crownGrad)" stroke="#b8860b" stroke-width="2" />
                <circle cx="32" cy="6" r="4" fill="#fff3c4" />
                <defs>
                  <linearGradient id="crownGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stop-color="#ffe89a" />
                    <stop offset="1" stop-color="#e0a72f" />
                  </linearGradient>
                </defs>
              </svg>
              <div class="avatar-ring" :style="{ '--ring': medal[item.rank]?.color, '--glow': medal[item.rank]?.glow }">
                <span class="avatar">{{ item.username.slice(0, 1).toUpperCase() }}</span>
              </div>
              <div class="winner-name" :class="titleClass(item.title)">{{ item.username }}</div>
              <el-tag size="small" effect="dark" round :color="medal[item.rank]?.color" style="border: none">
                {{ medal[item.rank]?.label }}
              </el-tag>
              <div class="winner-score">{{ item.monkey_score }} <small>小猴值</small></div>
              <div class="winner-meta">{{ item.solved_count }} 题 · 信用 {{ item.credit_score }}</div>
              <span v-if="item.title" class="title-chip" :class="titleClass(item.title)">{{ item.title }}</span>
            </div>
            <div class="podium-block">
              <span class="place-no">{{ item?.rank || idx + 1 }}</span>
            </div>
          </article>
        </div>
      </section>

      <el-card shadow="never" class="table-card">
        <el-table :data="rest" stripe>
          <el-table-column label="排名" width="90">
            <template #default="{ row }">
              <span class="rank-no">{{ row.rank }}</span>
            </template>
          </el-table-column>
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <div class="user-cell">
                <el-avatar :size="30">{{ row.username.slice(0, 1).toUpperCase() }}</el-avatar>
                <span :class="titleClass(row.title)">{{ row.username }}</span>
                <el-tag v-if="row.title" size="small" :type="row.title.includes('棕') ? 'danger' : 'warning'">
                  {{ row.title }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="monkey_score" label="小猴值" width="120" sortable />
          <el-table-column prop="solved_count" label="通过题数" width="120" />
          <el-table-column label="信用分" width="120">
            <template #default="{ row }">
              <el-tag :type="row.credit_score >= 100 ? 'success' : 'danger'" effect="light">
                {{ row.credit_score }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'banned' ? 'danger' : 'success'" effect="plain">
                {{ row.status === 'banned' ? '已封禁' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <EmptyState
          v-if="!rows.length"
          title="排行榜还是空的"
          description="完成官方比赛或获得小猴值后，就会出现在这里。"
        />
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.ranking-page { max-width: 1100px; margin: 0 auto; }
.podium-wrap { position: relative; margin: 8px 0 28px; }
.podium-glow {
  position: absolute; inset: 10% 18% auto; height: 240px;
  background: radial-gradient(circle, rgba(255, 196, 82, .22), transparent 65%);
  filter: blur(20px); pointer-events: none;
}
.podium { display: flex; align-items: flex-end; justify-content: center; gap: 18px; position: relative; }
.podium-item { width: 210px; text-align: center; }
.winner { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 14px; }
.crown { width: 54px; height: 34px; margin-bottom: -6px; filter: drop-shadow(0 4px 8px rgba(190,140,20,.3)); }
.avatar-ring {
  padding: 4px; border-radius: 50%;
  background: conic-gradient(var(--ring), #fff, var(--ring));
  box-shadow: 0 0 24px var(--glow);
}
.avatar {
  display: grid; place-items: center; width: 66px; height: 66px; border-radius: 50%;
  background: #fff; font-size: 26px; font-weight: 700; color: var(--text-strong);
}
.place-1 .avatar { width: 82px; height: 82px; font-size: 32px; }
.winner-name { font-size: 17px; font-weight: 700; }
.winner-name.brown { color: #8b5a2b; }
.winner-score { font-size: 22px; font-weight: 800; color: var(--accent); }
.winner-score small { font-size: 11px; color: var(--muted); font-weight: 500; }
.winner-meta { font-size: 12px; color: var(--muted); }
.title-chip { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: #fff7e6; color: #b7791f; }
.title-chip.brown { background: #f3e7da; color: #7a4a1d; }
.podium-block {
  height: 110px; border-radius: 14px 14px 0 0;
  background: linear-gradient(180deg, rgba(255,255,255,.9), rgba(240,244,250,.9));
  border: 1px solid var(--border); border-bottom: none;
  display: flex; align-items: flex-start; justify-content: center; padding-top: 14px;
  box-shadow: 0 -8px 30px rgba(31,45,70,.06);
}
.place-1 .podium-block { height: 150px; background: linear-gradient(180deg, #fff7df, #f5e6bb); }
.place-2 .podium-block { height: 120px; }
.place-3 .podium-block { height: 96px; }
.place-no { font-size: 34px; font-weight: 800; color: rgba(31,45,70,.22); }
.table-card { border-radius: 16px; }
.rank-no { font-weight: 700; color: var(--muted); }
.user-cell { display: flex; align-items: center; gap: 8px; }
.gold { color: #b8860b; font-weight: 700; }
.brown { color: #8b5a2b; font-weight: 700; }
@media (max-width: 760px) {
  .podium { gap: 6px; }
  .podium-item { width: 31%; }
  .avatar, .place-1 .avatar { width: 48px; height: 48px; font-size: 20px; }
  .winner-meta { display: none; }
}
</style>
