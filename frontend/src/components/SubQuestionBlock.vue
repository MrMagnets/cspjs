<script setup>
import { computed } from 'vue'
import MarkdownView from './MarkdownView.vue'
import { answerText } from '@/utils/format'

const props = defineProps({
  sub: { type: Object, required: true },
  index: { type: Number, default: 1 },
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  result: { type: Object, default: null },
  showAnswer: { type: Boolean, default: false },
  hideAnalysis: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const selected = computed(() => (props.modelValue || '').toUpperCase())
const correct = computed(() => (props.sub.correct_answer || '').toUpperCase())
const showResult = computed(() => Boolean(props.result) || props.showAnswer)
const analysis = computed(() => props.sub.analysis_md || '')
const unanswered = computed(() => Boolean(props.result) && !props.result.user_answer)

const resultLabel = computed(() => {
  if (unanswered.value) return '未作答'
  return props.result?.is_correct ? '回答正确' : '回答错误'
})

const resultPillClass = computed(() => {
  if (unanswered.value) return 'neutral'
  return props.result?.is_correct ? 'ok' : 'bad'
})

function optionClass(key) {
  const k = key.toUpperCase()
  if (showResult.value) {
    if (correct.value.includes(k)) return 'correct'
    if (selected.value === k) return 'wrong'
    return ''
  }
  return selected.value === k ? 'active' : ''
}

function pick(key) {
  if (props.disabled) return
  emit('update:modelValue', key.toUpperCase())
}
</script>

<template>
  <section class="sub-question">
    <header class="sub-head">
      <span class="sub-badge">{{ index }}</span>
      <div class="sub-title">
        <MarkdownView v-if="sub.content_md" :content="sub.content_md" />
        <span v-else class="muted">请选择正确答案</span>
      </div>
    </header>

    <div class="options">
      <div
        v-for="option in sub.options"
        :key="option.key"
        class="option-item"
        :class="[optionClass(option.key), { disabled }]"
        role="radio"
        :aria-checked="selected === String(option.key).toUpperCase()"
        tabindex="0"
        @click="pick(option.key)"
        @keydown.enter.prevent="pick(option.key)"
        @keydown.space.prevent="pick(option.key)"
      >
        <span class="option-key">{{ option.key }}</span>
        <span class="option-text">
          <MarkdownView :content="option.text" />
        </span>
      </div>
    </div>

    <div v-if="result" class="sub-result">
      <span class="pill" :class="resultPillClass">{{ resultLabel }}</span>
      <span class="answer-line">
        你的答案：<b>{{ answerText(result.user_answer) }}</b>
        <span class="dot-sep">·</span>
        正确答案：<b>{{ result.correct_answer }}</b>
      </span>
    </div>

    <div v-if="showResult && analysis && !hideAnalysis" class="analysis">
      <div class="analysis-title">解析</div>
      <MarkdownView :content="analysis" />
    </div>
  </section>
</template>

<style scoped>
.sub-question {
  padding: 18px 0 6px;
}

.sub-question + .sub-question {
  border-top: 1px dashed var(--border);
  margin-top: 8px;
}

.sub-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.sub-title {
  flex: 1;
  min-width: 0;
  padding-top: 1px;
}

.options {
  margin: 12px 0 4px 38px;
}

@media (max-width: 640px) {
  .options {
    margin-left: 0;
  }
}

.option-item.disabled {
  cursor: default;
}

.option-text {
  flex: 1;
  min-width: 0;
}

.option-text :deep(.markdown-body) {
  font-size: 15px;
  line-height: 1.7;
}

.option-text :deep(.markdown-body p) {
  margin: 0;
}

.sub-result {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 10px 0 4px 38px;
  font-size: 13.5px;
  color: var(--muted);
}

@media (max-width: 640px) {
  .sub-result {
    margin-left: 0;
  }
}

.pill {
  padding: 1px 10px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
}

.pill.ok {
  background: var(--ok-soft);
  color: #1d7a52;
}

.pill.bad {
  background: var(--bad-soft);
  color: #a33b38;
}

.pill.neutral {
  background: #eef2f6;
  color: #6b7c93;
}

.answer-line b {
  color: var(--text);
  font-family: var(--mono);
}

.dot-sep {
  color: #c8d2dd;
  margin: 0 4px;
}

.analysis {
  margin: 12px 0 8px 38px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-left: 3px solid var(--brand);
  border-radius: 8px;
}

@media (max-width: 640px) {
  .analysis {
    margin-left: 0;
  }
}

.analysis-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--brand-dark);
  margin-bottom: 4px;
  letter-spacing: 0.5px;
}
</style>
