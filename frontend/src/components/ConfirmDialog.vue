<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { dialogState, settleDialog } from '@/composables/useConfirmDialog'

const inputRef = ref(null)
const localError = ref('')

const isPrompt = computed(() => dialogState.kind === 'prompt')
const showCancel = computed(() => dialogState.cancelText !== '')

watch(
  () => dialogState.visible,
  async (visible) => {
    localError.value = ''
    if (visible && isPrompt.value) {
      await nextTick()
      inputRef.value?.focus?.()
    }
  },
)

function onVisibleChange(visible) {
  if (!visible) settleDialog(false)
}

function submit() {
  if (isPrompt.value) {
    const value = (dialogState.value || '').trim()
    if (dialogState.required && !value) {
      localError.value = '该项为必填内容'
      return
    }
    settleDialog(value)
    return
  }
  settleDialog(true)
}

function cancel() {
  settleDialog(false)
}
</script>

<template>
  <el-dialog
    :model-value="dialogState.visible"
    :width="dialogState.width"
    :show-close="true"
    align-center
    append-to-body
    class="confirm-dialog"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
  >
    <template #header>
      <div class="cd-header">
        <span class="cd-icon" :class="{ danger: dialogState.danger }">!</span>
        <span class="cd-title">{{ dialogState.title }}</span>
      </div>
    </template>

    <div class="cd-body">
      <p v-if="dialogState.message" class="cd-message">{{ dialogState.message }}</p>
      <el-input
        v-if="isPrompt"
        ref="inputRef"
        v-model="dialogState.value"
        type="textarea"
        :rows="3"
        :maxlength="dialogState.maxlength"
        show-word-limit
        :placeholder="dialogState.placeholder"
        @keydown.ctrl.enter="submit"
      />
      <p v-if="isPrompt && !localError && dialogState.hint" class="cd-hint">{{ dialogState.hint }}</p>
      <p v-if="localError" class="cd-error">{{ localError }}</p>
    </div>

    <template #footer>
      <div class="cd-footer">
        <el-button v-if="showCancel" @click="cancel">{{ dialogState.cancelText }}</el-button>
        <el-button :type="dialogState.danger ? 'danger' : 'primary'" @click="submit">
          {{ dialogState.confirmText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.cd-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cd-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 17px;
}

.cd-icon.danger {
  background: var(--bad-soft);
  color: var(--bad);
}

.cd-title {
  font-size: 16.5px;
  font-weight: 700;
  color: var(--text);
}

.cd-body {
  padding: 2px 2px 6px;
}

.cd-message {
  margin: 0 0 12px;
  color: #41525f;
  line-height: 1.75;
  white-space: pre-wrap;
}

.cd-hint {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--muted);
}

.cd-error {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--bad);
}

.cd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
