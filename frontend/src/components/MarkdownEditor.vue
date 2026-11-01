<script setup>
import { ref } from 'vue'
import MarkdownView from './MarkdownView.vue'

defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: Number, default: 8 },
  placeholder: { type: String, default: '支持 Markdown 与 KaTeX 公式，例如 $O(n \\log n)$、$$\\sum_{i=1}^{n} i$$' },
  minHeight: { type: String, default: '' },
  showTip: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])
const tab = ref('edit')
</script>

<template>
  <div class="md-editor">
    <el-tabs v-model="tab" class="md-tabs">
      <el-tab-pane label="编辑" name="edit">
        <el-input
          :model-value="modelValue"
          type="textarea"
          :rows="rows"
          :placeholder="placeholder"
          :style="minHeight ? { minHeight } : undefined"
          @update:model-value="emit('update:modelValue', $event)"
        />
      </el-tab-pane>
      <el-tab-pane label="预览" name="preview">
        <div class="md-preview" :style="minHeight ? { minHeight } : undefined">
          <MarkdownView v-if="modelValue" :content="modelValue" />
          <p v-else class="muted preview-empty">暂无内容</p>
        </div>
      </el-tab-pane>
    </el-tabs>
    <p v-if="showTip" class="md-tip">
      行内公式 <code>$...$</code>，块级公式 <code>$$...$$</code>；代码块用三个反引号包裹并标注语言（如 ```cpp）。
    </p>
  </div>
</template>

<style scoped>
.md-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.md-tabs :deep(.el-tabs__item) {
  height: 34px;
  font-size: 13px;
}

.md-preview {
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 14px 16px;
  background: #fcfdfe;
  min-height: 120px;
}

.preview-empty {
  margin: 0;
  font-size: 13px;
}

.md-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.md-tip code {
  font-family: var(--mono);
  background: #f1f3f6;
  padding: 1px 5px;
  border-radius: 4px;
}
</style>
