<script setup>
import { computed } from 'vue'
import { percent } from '@/utils/format'

const props = defineProps({
  label: { type: String, required: true },
  total: { type: Number, default: 0 },
  correct: { type: Number, default: 0 },
  accuracy: { type: Number, default: 0 },
  hint: { type: String, default: '' },
})

const tone = computed(() => {
  if (props.accuracy >= 0.8) return 'ok'
  if (props.accuracy >= 0.5) return 'warn'
  return 'bad'
})

const width = computed(() => `${Math.max(0, Math.min(1, props.accuracy)) * 100}%`)
</script>

<template>
  <div class="stat-bar">
    <div class="sb-head">
      <span class="sb-label">{{ label }}</span>
      <span class="sb-value" :class="tone">{{ percent(accuracy) }}</span>
    </div>
    <div class="sb-track">
      <div class="sb-fill" :class="tone" :style="{ width }" />
    </div>
    <div class="sb-meta">
      {{ correct }} / {{ total }} 题正确
      <span v-if="hint"> · {{ hint }}</span>
    </div>
  </div>
</template>

<style scoped>
.stat-bar {
  padding: 8px 0;
}

.sb-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.sb-label {
  font-size: 14px;
  color: var(--text);
  font-weight: 550;
}

.sb-value {
  font-family: var(--mono);
  font-size: 13.5px;
  font-weight: 700;
}

.sb-value.ok {
  color: var(--ok);
}

.sb-value.warn {
  color: var(--warn);
}

.sb-value.bad {
  color: var(--bad);
}

.sb-track {
  height: 8px;
  border-radius: 999px;
  background: #eef2f6;
  overflow: hidden;
}

.sb-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.sb-fill.ok {
  background: linear-gradient(90deg, #37b07c, #2f9e6b);
}

.sb-fill.warn {
  background: linear-gradient(90deg, #e7bc55, #d9a12c);
}

.sb-fill.bad {
  background: linear-gradient(90deg, #e2726e, #d9534f);
}

.sb-meta {
  margin-top: 5px;
  font-size: 12px;
  color: var(--muted);
}
</style>
