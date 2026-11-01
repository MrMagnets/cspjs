<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { SOURCE_LABELS, STATUS_META, TYPE_SHORT, formatDate } from '@/utils/format'

const props = defineProps({
  problem: { type: Object, required: true },
  showStatus: { type: Boolean, default: false },
})

const router = useRouter()

const sourceLabel = computed(() => {
  const p = props.problem
  const parts = [SOURCE_LABELS[p.source_tag] || p.source_tag]
  if (p.source_year) parts.push(`${p.source_year}`)
  if (p.source_exam) parts.push(p.source_exam)
  return parts.filter(Boolean).join(' · ')
})

function open() {
  router.push({ name: 'problem-detail', params: { id: props.problem.id } })
}
</script>

<template>
  <article class="problem-card" @click="open">
    <div class="pc-head">
      <span class="type-badge" :class="problem.type">{{ TYPE_SHORT[problem.type] }}</span>
      <el-tag
        v-if="showStatus && problem.status !== 'approved'"
        size="small"
        :type="STATUS_META[problem.status]?.type"
        effect="light"
      >
        {{ STATUS_META[problem.status]?.label || problem.status }}
      </el-tag>
      <span class="spacer" />
      <span class="pc-date">{{ formatDate(problem.created_at) }}</span>
    </div>

    <h3 class="pc-title">{{ problem.title }}</h3>

    <div v-if="problem.tags?.length" class="pc-tags">
      <span v-for="tag in problem.tags" :key="tag.id" class="pc-tag">{{ tag.name }}</span>
    </div>

    <div class="pc-foot">
      <span>{{ sourceLabel }}</span>
      <span class="dot-sep">·</span>
      <span>{{ problem.sub_question_count }} 个小题</span>
      <span v-if="problem.contributor_name" class="dot-sep">·</span>
      <span v-if="problem.contributor_name">by {{ problem.contributor_name }}</span>
    </div>

    <p v-if="showStatus && problem.status === 'rejected' && problem.reject_reason" class="pc-reject">
      驳回原因：{{ problem.reject_reason }}
    </p>
  </article>
</template>

<style scoped>
.problem-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 9px;
  height: 100%;
}

.problem-card:hover {
  border-color: #c3ded5;
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.pc-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pc-date {
  font-size: 12px;
  color: var(--muted);
}

.pc-title {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  line-height: 1.5;
  color: var(--text);
}

.pc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pc-tag {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #f2f5f8;
  color: #55697a;
}

.pc-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 12.5px;
  color: var(--muted);
  margin-top: auto;
}

.dot-sep {
  color: #c8d2dd;
}

.pc-reject {
  margin: 0;
  font-size: 12.5px;
  color: var(--bad);
  background: var(--bad-soft);
  border-radius: 8px;
  padding: 6px 10px;
}
</style>
